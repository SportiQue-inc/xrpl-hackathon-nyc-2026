"""Account model preferences never expand the service allowlist or alter trade rules."""
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'prototypes/data-vault-market/server'))
os.environ.setdefault('VM_DATA_DIR', tempfile.mkdtemp(prefix='vault-model-tests-'))
from vaultmarket import agents, config, llm, rail
from vaultmarket.market import Market
from vaultmarket.store import Store


@pytest.fixture
def models(monkeypatch):
    monkeypatch.setattr(config, 'LLM_PROVIDER', 'openai')
    monkeypatch.setattr(config, 'OPENAI_MODELS', ['allowed-a', 'allowed-b'])
    monkeypatch.setattr(config, 'OPENAI_MODEL', 'allowed-a')
    monkeypatch.setattr(config, 'LLM_RPM', 100)
    monkeypatch.setattr(config, 'LLM_DAILY_CALLS', 100000)
    monkeypatch.setattr(llm, '_calls', [])
    monkeypatch.setattr(llm, '_rest', {})
    monkeypatch.setattr(llm, 'USAGE', {'calls': 0, 'fallbacks': 0, 'in_tokens': 0, 'out_tokens': 0,
                                    'day': time.strftime('%Y-%m-%d', time.gmtime()), 'provider': 'openai'})
    llm.budget(None)
    return monkeypatch


@pytest.fixture
def web_market(tmp_path, monkeypatch, models):
    monkeypatch.setattr(config, 'LEDGER', 'mock')
    monkeypatch.setattr(config, 'DB_PATH', str(tmp_path / 'models.db'))
    monkeypatch.setattr(config, 'PUBLIC', True)
    monkeypatch.setattr(rail, 'KEYS_FILE', str(tmp_path / 'keys.json'))
    m = Market()
    for aid in ('u-owner', 'u-other'):
        m.s.insert('accounts', id=aid, name=aid, type='person',
                   sell_agent={'mode': 'ask', 'min': {'sleep_log': 7}, 'blocks': []},
                   buy_agent={'auto_limit': 100, 'min_trust': .7, 'max_overlap': .3})
    m.s.insert('users', username='owner', account='u-owner')
    m.s.insert('sessions', token='owner-token', username='owner')
    from vaultmarket import app as web
    monkeypatch.setattr(web, 'M', m)
    client = TestClient(web.app)
    client.cookies.set(web.COOKIE, 'owner-token')
    return client, m


def test_models_expose_only_current_provider_allowlist(web_market, models):
    client, _ = web_market
    assert client.get('/api/meta').json()['models'] == ['auto', 'allowed-a', 'allowed-b']
    models.setattr(config, 'LLM_PROVIDER', 'none')
    assert client.get('/api/meta').json()['models'] == ['auto']


@pytest.mark.parametrize('bad', ['external-model', None, [], {'model': 'allowed-a'}])
def test_rejects_invalid_selection_without_partial_write(web_market, bad):
    client, market = web_market
    response = client.post('/api/account/u-owner/settings', json={
        'sell_agent': {'model': 'allowed-a', 'min': {'sleep_log': 99}}, 'buy_agent': {'model': bad}})
    assert response.status_code == 400
    assert market.acct('u-owner')['sell_agent']['min']['sleep_log'] == 7
    assert 'model' not in market.acct('u-owner')['sell_agent']


def test_account_preferences_persist_independently_and_keep_owner_guard(web_market):
    client, market = web_market
    body = {'sell_agent': {'model': 'allowed-a'}, 'buy_agent': {'model': 'allowed-b'}}
    assert client.post('/api/account/u-other/settings', json=body).status_code == 403
    assert client.post('/api/account/u-owner/settings', json=body).status_code == 200
    assert client.post('/api/account/u-owner/settings', json={'buy_agent': {'auto_limit': 50}}).status_code == 200
    reopened = Store(config.DB_PATH)
    try:
        row = reopened.one('SELECT sell_agent,buy_agent FROM accounts WHERE id=?', ('u-owner',))
        assert json.loads(row['sell_agent'])['model'] == 'allowed-a'
        assert json.loads(row['buy_agent']) == {'model': 'allowed-b', 'auto_limit': 50, 'min_trust': .7, 'max_overlap': .3}
    finally:
        reopened.db.close()
    assert client.post('/api/account/u-owner/settings', json={'buy_agent': {'model': 'auto'}}).status_code == 200
    assert market.acct('u-owner')['sell_agent']['model'] == 'allowed-a'


def client_reply(models, create):
    models.setattr(llm, '_client', SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))


def response(model, content='{"message":"Agreed","thinking":"Owner terms fit","verdict":"agree","price":8}'):
    return SimpleNamespace(model=model, choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
                           usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5))


def test_selected_model_is_used_and_actual_source_is_recorded(models):
    seen = []
    def create(**kw):
        seen.append(kw['model'])
        return response(kw['model'] + '-snapshot')
    client_reply(models, create)
    w = {'kind': 'sleep_log', 'purpose': 'sleep research', 'max': 20, 'offer': 8}
    buyer = agents.buyer_open('Buyer', w, 0, model='allowed-b')
    seller = agents.seller_reply('Seller', {'min': {'sleep_log': 7}, 'model': 'allowed-a'}, w, 'Buyer', 1)
    close = agents.buyer_close('Buyer', w, {'agreed': 1, 'declined': 0, 'overlap': 0, 'total': 8, 'ok': True}, model='allowed-b')
    assert seen == ['allowed-b', 'allowed-a', 'allowed-b']
    assert [buyer['by'], seller['by'], close['by']] == ['allowed-b-snapshot', 'allowed-a-snapshot', 'allowed-b-snapshot']
    assert seller['verdict'] == 'agree' and seller['price'] == 8


def test_explicit_rate_limit_uses_rules_while_auto_can_try_the_next_model(models):
    import httpx
    import openai
    seen = []
    def create(**kw):
        seen.append(kw['model'])
        if kw['model'] == 'allowed-a':
            req = httpx.Request('POST', 'https://example.invalid')
            raise openai.RateLimitError('insufficient_quota', response=httpx.Response(429, request=req), body={})
        return response(kw['model'])
    client_reply(models, create)
    assert llm.ask_json('system', 'prompt', model='allowed-a') is None
    assert seen == ['allowed-a'] and llm.model_name() == 'rules'
    assert llm.ask_json('system', 'prompt', model='allowed-a') is None
    assert seen == ['allowed-a'], 'The quota cooldown must still prevent another provider request'
    assert llm.ask_json('system', 'prompt') == {'message': 'Agreed', 'thinking': 'Owner terms fit', 'verdict': 'agree', 'price': 8}
    assert seen == ['allowed-a', 'allowed-b'] and llm.model_name() == 'allowed-b'


def test_invalid_model_and_caps_never_call_provider(models):
    def forbidden(**_):
        raise AssertionError('Provider must not be called')
    client_reply(models, forbidden)
    assert llm.ask_json('system', 'prompt', model='external-model') is None
    models.setattr(config, 'LLM_DAILY_CALLS', 0)
    assert llm.ask_json('system', 'prompt', model='allowed-a') is None
    assert llm.model_name() == 'rules'


def test_bad_json_clears_prior_success_source(models):
    contents = iter(['{"message":"ok"}', 'not JSON'])
    client_reply(models, lambda **kw: response(kw['model'], next(contents)))
    assert llm.ask_json('system', 'prompt', model='allowed-a') == {'message': 'ok'}
    assert llm.ask_json('system', 'prompt', model='allowed-b') is None
    assert llm.model_name() == 'rules'


def test_chat_parser_uses_owning_side_preference(models):
    seen = []
    def create(**kw):
        seen.append(kw['model'])
        return response(kw['model'], '{"intent":"other","kind":null,"price":null}')
    client_reply(models, create)
    agents.parse_chat('buy something unusual', sell_model='allowed-a', buy_model='allowed-b')
    agents.parse_chat('help with my data', sell_model='allowed-a', buy_model='allowed-b')
    assert seen == ['allowed-b', 'allowed-a']


@pytest.mark.parametrize('side', ['sell_agent', 'buy_agent'])
def test_agent_settings_reject_non_objects(web_market, side):
    client, _ = web_market
    assert client.post('/api/account/u-owner/settings', json={side: []}).status_code == 400


@pytest.mark.parametrize('cap', ['minute', 'thread'])
def test_selected_model_keeps_minute_and_thread_caps(models, cap):
    calls = []
    client_reply(models, lambda **kw: calls.append(kw) or response(kw['model']))
    if cap == 'minute':
        models.setattr(config, 'LLM_RPM', 0)
    else:
        llm.budget(0)
    try:
        assert llm.ask_json('system', 'prompt', model='allowed-b') is None
        assert calls == [] and llm.model_name() == 'rules'
    finally:
        llm.budget(None)
