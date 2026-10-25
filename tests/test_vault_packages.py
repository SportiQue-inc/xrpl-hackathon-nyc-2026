"""Commercial snapshots reuse actual mock escrow delivery, never fabricated paid rows."""
import hashlib
import json
import random
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'prototypes/data-vault-market/server'))
from vaultmarket import config, data, rail
from vaultmarket.market import Market
from vaultmarket.vaultfiles import register as register_files


@pytest.fixture
def commerce(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'LEDGER', 'mock')
    monkeypatch.setattr(config, 'LLM_PROVIDER', 'none')
    monkeypatch.setattr(config, 'ASSET', 'XRP')
    monkeypatch.setattr(config, 'MICRO_PER_UNIT', 10000)
    monkeypatch.setattr(config, 'DB_PATH', str(tmp_path / 'market.db'))
    monkeypatch.setattr(rail, 'KEYS_FILE', str(tmp_path / 'keys.json'))
    m = Market()
    for aid in ('a', 'b', 'c'):
        m.s.insert('accounts', id=aid, name=aid, type='org', trust=.95, verified=1,
                   sell_agent={'mode': 'auto', 'min': {}, 'blocks': []},
                   buy_agent={'auto_limit': 1000, 'min_trust': .7})
        m.addr[aid] = m.rail.ensure_account(aid)
    def guard(request, aid, write=True):
        if request.headers.get('x-owner') != aid:
            raise HTTPException(403, 'owner required')
        return {'account': aid}
    app = FastAPI()
    register_files(app, m, guard)
    from vaultmarket.packages import register
    register(app, m, guard)
    return m, TestClient(app)


def original(m, aid, kind, day=0):
    body = data.make_record(kind, random.Random(day + 33), 'Synthetic', day, (40.7, -74))
    return m.add_file(aid, kind, 'original.json', body, listed=True, source='synthetic')


def sale(m, seller, buyer, kind, fid, resale=True):
    p = m.s.insert('postings', buyer=buyer, kind=kind, offer=2, max=2, purpose='research',
                   lot=1, resale=int(resale), min_trust=.7, status='open', once=1)
    c = m.s.insert('contracts', posting=p, buyer=buyer, seller=seller, kind=kind,
                   status='negotiating', asset=m.rail.symbol(), unit_micro=config.MICRO_PER_UNIT)
    m.settle(c, m.s.one('SELECT * FROM postings WHERE id=?', (p,)),
             [(seller, [m.s.one('SELECT * FROM files WHERE id=?', (i,)) for i in (fid if isinstance(fid, list) else [fid])], 2)], {'protocol': [], 'tx': []}, 2)
    return m.s.one('SELECT * FROM files WHERE source=? AND account=?', (f'contract {c}', buyer))


def publish(client, aid, files, **changes):
    h = {'x-owner': aid}
    r = client.post(f'/api/account/{aid}/collections', headers=h, json={'name': 'Sleep and routes', 'files': files})
    assert r.status_code == 200, r.text
    body = {'collection': r.json()['id'], 'version': 1, 'price': .05, 'purpose': 'research', 'resale': True, **changes}
    return client.post(f'/api/account/{aid}/packages', headers=h, json=body)


def buy(client, aid, listing, **changes):
    return client.post(f'/api/account/{aid}/packages/{listing["id"]}/buy', headers={'x-owner': aid},
                       json={k: listing[k] for k in ('sha256', 'price', 'purpose', 'resale')} | changes)


def test_mixed_purchase_preserves_complete_payload_and_private_origin(commerce):
    m, client = commerce
    sleep = original(m, 'a', 'sleep_log')
    purchased = sale(m, 'a', 'c', 'sleep_log', sleep)
    gps = original(m, 'c', 'gps_track', 2)
    r = publish(client, 'c', [purchased['id'], gps])
    assert r.status_code == 200, r.text
    listing = r.json()
    assert set(listing['kinds']) == {'sleep_log', 'gps_track'}
    before = client.get('/api/packages?account=b', headers={'x-owner': 'b'})
    assert before.status_code == 200
    for private in ('fingerprints', 'source_contracts', 'nights', 'points', 'derived_from'):
        assert private not in before.text
    result = buy(client, 'b', listing)
    assert result.status_code == 200, result.text
    assert result.json()['status'] == 'settled'
    acquired = m.s.one('SELECT * FROM files WHERE account=? AND source=?', ('b', f'contract {result.json()["contract"]}'))
    dl = client.get(f'/api/account/b/file/{acquired["id"]}/download', headers={'x-owner': 'b'})
    assert dl.status_code == 200
    assert len(dl.json()['records'][0]['records'][0]['payload']['records'][0]['nights']) == 7
    assert dl.headers['x-vault-sha256'] == hashlib.sha256(dl.content).hexdigest()
    assert client.get(f'/api/account/b/file/{acquired["id"]}/download', headers={'x-owner': 'c'}).status_code == 403
    assert json.loads(acquired['fps']) == sorted(set(json.loads(purchased['fps'])) | set(json.loads(m.s.one('SELECT fps FROM files WHERE id=?', (gps,))['fps'])))
    assert buy(client, 'b', listing).json()['status'] == 'rejected'


def test_original_a_to_b_then_a_to_c_to_b_rejects_before_payment(commerce):
    m, client = commerce
    sleep = original(m, 'a', 'sleep_log')
    sale(m, 'a', 'b', 'sleep_log', sleep)
    c_copy = sale(m, 'a', 'c', 'sleep_log', sleep)
    listing = publish(client, 'c', [c_copy['id'], original(m, 'c', 'gps_track', 2)]).json()
    txs = m.s.one('SELECT COUNT(*) n FROM txs')['n']
    balance = m.rail.balance(m.addr['b'])
    result = buy(client, 'b', listing).json()
    assert result['status'] == 'rejected' and 'already owns' in result['reason']
    assert m.s.one('SELECT COUNT(*) n FROM txs')['n'] == txs
    assert m.rail.balance(m.addr['b']) == balance
    assert m.s.one('SELECT COUNT(*) n FROM files WHERE account=? AND kind=?', ('b', 'data_package'))['n'] == 0


def test_mixed_then_original_cannot_charge_twice(commerce):
    m, client = commerce
    sleep = original(m, 'a', 'sleep_log')
    listing = publish(client, 'a', [sleep, original(m, 'a', 'gps_track', 2)]).json()
    assert buy(client, 'b', listing).json()['status'] == 'settled'
    before = m.s.one('SELECT COUNT(*) n FROM txs')['n']
    assert sale(m, 'a', 'b', 'sleep_log', sleep) is None
    assert m.s.one('SELECT COUNT(*) n FROM txs')['n'] == before


def test_unlicensed_payload_bad_terms_and_other_owner_are_blocked(commerce):
    m, client = commerce
    acquired = sale(m, 'a', 'c', 'sleep_log', original(m, 'a', 'sleep_log'), resale=False)
    assert publish(client, 'c', [acquired['id']]).status_code == 400
    own = original(m, 'a', 'gps_track', 2)
    listing = publish(client, 'a', [own], resale=False).json()
    assert buy(client, 'b', listing, resale=True).status_code == 409
    assert buy(client, 'b', listing, purpose='insurance pricing').status_code == 409
    assert buy(client, 'b', listing, sha256='changed').status_code == 409
    assert buy(client, 'b', listing, price=.01).json()['status'] == 'rejected'
    assert client.get('/api/packages?account=b').status_code == 403
    assert client.post('/api/account/a/packages', headers={'x-owner': 'b'}, json={}).status_code == 403


def test_immutable_package_survives_collection_changes_and_recovery(commerce, monkeypatch):
    m, client = commerce
    sleep = original(m, 'a', 'sleep_log')
    listing = publish(client, 'a', [sleep, original(m, 'a', 'gps_track', 2)]).json()
    expected = m.s.one('SELECT clean,fps FROM files WHERE id=(SELECT file FROM data_packages WHERE id=?)', (listing['id'],))
    def crash(*args, **kwargs):
        raise RuntimeError('synthetic crash after validated finish')
    original_open = m.rail.open
    monkeypatch.setattr(m.rail, 'open', crash)
    with pytest.raises(RuntimeError, match='synthetic crash'):
        buy(client, 'b', listing)
    monkeypatch.setattr(m.rail, 'open', original_open)
    before = m.s.one('SELECT COUNT(*) n FROM escrows')['n']
    assert buy(client, 'b', listing).json()['status'] == 'rejected'
    assert sale(m, 'a', 'b', 'sleep_log', sleep) is None
    assert m.s.one('SELECT COUNT(*) n FROM escrows')['n'] == before
    m.recover(); m.recover()
    c = m.s.one("SELECT * FROM contracts WHERE buyer='b' AND status='settled'")
    assert c['status'] == 'settled'
    bought = m.s.q("SELECT * FROM files WHERE account='b'")
    assert len(bought) == 1
    assert json.loads(bought[0]['raw'])['records'] == [json.loads(expected['clean'])]
    assert bought[0]['fps'] == expected['fps']
    assert m.s.one('SELECT COUNT(*) n FROM txs WHERE contract=?', (c['id'],))['n'] == 2


def test_all_four_acquired_files_survive_three_file_preview(commerce):
    m, client = commerce
    files = [original(m, 'a', 'sleep_log', n * 8) for n in range(4)]
    acquired = sale(m, 'a', 'c', 'sleep_log', files)
    assert len(json.loads(acquired['clean'])['records']) == 3
    assert len(json.loads(acquired['raw'])['records']) == 4
    listing = publish(client, 'c', [acquired['id'], original(m, 'c', 'gps_track', 2)]).json()
    result = buy(client, 'b', listing).json()
    bought = m.s.one('SELECT raw FROM files WHERE account=? AND source=?', ('b', f'contract {result["contract"]}'))
    assert len(json.loads(bought['raw'])['records'][0]['records'][0]['payload']['records']) == 4


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '1e999999999', 0, -2, True])
def test_invalid_price_fails_before_payment(commerce, value):
    m, client = commerce
    fid = original(m, 'a', 'gps_track')
    assert publish(client, 'a', [fid], price=value).status_code == 400
    listing = publish(client, 'a', [fid]).json()
    assert buy(client, 'b', listing, price=value).status_code == 400
    assert m.s.one('SELECT COUNT(*) n FROM escrows')['n'] == 0


def test_sources_must_keep_purpose_and_no_internal_duplicate_records(commerce):
    m, client = commerce
    sleep = original(m, 'a', 'sleep_log')
    acquired = sale(m, 'a', 'c', 'sleep_log', sleep)
    assert publish(client, 'c', [acquired['id']], purpose='insurance pricing').status_code == 400
    duplicate = m.s.insert('files', **{k: v for k, v in acquired.items() if k not in ('id', 'created')})
    assert publish(client, 'c', [acquired['id'], duplicate]).status_code == 400


def test_unrelated_shared_category_does_not_block_fresh_sale_queue(commerce):
    m, _ = commerce
    gps = original(m, 'a', 'gps_track')
    sale(m, 'a', 'b', 'gps_track', gps)
    original(m, 'a', 'sleep_log', 16)
    p = m.s.insert('postings', buyer='b', kind='sleep_log', offer=8, max=20, purpose='research',
                   lot=1, resale=0, min_trust=.7, status='open', once=1)
    m.enqueue_sale('a', 'sleep_log', p)
    assert m.process_sale_queue()
    assert m.s.one('SELECT status FROM contracts WHERE posting=?', (p,))['status'] == 'settled'
