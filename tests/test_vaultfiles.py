"""Owner-only downloads and immutable My DB collection references."""
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'prototypes/data-vault-market/server'))
from vaultmarket.store import Store
from vaultmarket.vaultfiles import register


@pytest.fixture
def vault(tmp_path):
    market = SimpleNamespace(s=Store(str(tmp_path / 'vault.db')), events=0)
    source = {'from_contract': 11, 'records': [{'value': n} for n in range(9)]}
    bought = market.s.insert('files', account='u-owner', kind='sleep_log', name='purchased.json',
                            raw=json.dumps(source), clean=json.dumps({'records': source['records'][:3]}),
                            status='bought', fps=['original-fingerprint'], source='contract 11', resale=0)
    own = market.s.insert('files', account='u-owner', kind='gps_track', name='own.json',
                         raw=json.dumps({'route': [1, 2], 'from_contract': 999, 'from_contracts': None}), clean='{}', status='private', fps=['own-fingerprint'], source='upload')
    other = market.s.insert('files', account='u-other', name='private.json', raw='{"private":true}', status='private')
    app = FastAPI()

    def guard(request, aid, write=True):
        owner = request.headers.get('x-owner')
        if owner != aid:
            raise HTTPException(403, 'owner required')
        return {'account': owner}

    register(app, market, guard)
    return TestClient(app), market, bought, own, other, source


def test_download_returns_full_delivered_payload_only_to_its_owner(vault):
    client, market, bought, _, _, expected = vault
    path = f'/api/account/u-owner/file/{bought}/download'
    assert client.get(path).status_code == 403
    assert client.get(path, headers={'x-owner': 'u-other'}).status_code == 403
    result = client.get(path, headers={'x-owner': 'u-owner'})
    assert result.status_code == 200
    assert result.json() == expected
    assert len(result.json()['records']) == 9  # clean contains only a 3-record preview
    assert result.headers['x-vault-sha256'] == hashlib.sha256(result.content).hexdigest()
    assert 'attachment' in result.headers['content-disposition']
    assert result.headers['cache-control'] == 'private, no-store'
    assert client.get(f'/api/account/u-owner/file/{999}/download', headers={'x-owner': 'u-owner'}).status_code == 404


def test_collections_reference_entire_owned_db_and_preserve_old_revisions(vault):
    client, market, bought, own, _, _ = vault
    headers = {'x-owner': 'u-owner'}
    before = market.s.q('SELECT * FROM files ORDER BY id')
    first = client.post('/api/account/u-owner/collections', headers=headers, json={'name': 'My research DB', 'files': [own, bought]})
    assert first.status_code == 200, first.text
    cid = first.json()['id']
    original = client.get(f'/api/account/u-owner/collections/{cid}/versions/1/manifest', headers=headers)
    manifest = original.json()
    assert manifest['version'] == 1
    assert {f['id'] for f in manifest['files']} == {own, bought}
    purchase = next(f for f in manifest['files'] if f['id'] == bought)
    assert purchase['source_contracts'] == [11]
    assert next(f for f in manifest['files'] if f['id'] == own)['source_contracts'] == []  # upload contents cannot assert a purchase
    assert purchase['license']['resale_allowed'] is False
    assert purchase['fingerprints'] == ['original-fingerprint']
    assert first.json()['sha256'] == hashlib.sha256(original.content).hexdigest()
    second = client.post(f'/api/account/u-owner/collections/{cid}/versions', headers=headers, json={'files': [bought]})
    assert second.status_code == 200
    assert second.json()['version'] == 2
    assert client.get(f'/api/account/u-owner/collections/{cid}/versions/1/manifest', headers=headers).content == original.content
    listed = client.get('/api/account/u-owner/collections', headers=headers).json()['collections']
    assert [v['version'] for v in listed[0]['versions']] == [2, 1]
    assert market.s.q('SELECT * FROM files ORDER BY id') == before
    assert market.events == 2


def test_collection_rejects_other_owners_file_and_bad_input(vault):
    client, _, bought, own, other, _ = vault
    url = '/api/account/u-owner/collections'
    headers = {'x-owner': 'u-owner'}
    assert client.get(url).status_code == 403
    assert client.post(url, headers={'x-owner': 'u-other'}, json={'name': 'x', 'files': [bought]}).status_code == 403
    assert client.post(url, headers=headers, json={'name': 'x', 'files': [other]}).status_code == 404
    for body in ({'name': '', 'files': [own]}, {'name': 'x', 'files': []}, {'name': 'x', 'files': [True]}, {'name': 'x', 'files': '1'}):
        assert client.post(url, headers=headers, json=body).status_code == 400
    created = client.post(url, headers=headers, json={'name': 'x', 'files': [bought]}).json()
    path = f'/api/account/u-other/collections/{created["id"]}/versions/1/manifest'
    assert client.get(path, headers={'x-owner': 'u-other'}).status_code == 404
    assert client.post(f'{url}/{created["id"]}/versions', headers={'x-owner': 'u-other'}, json={'files': [own]}).status_code == 403
