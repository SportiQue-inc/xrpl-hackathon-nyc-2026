"""Owner-only payload downloads and append-only collections of existing vault files."""
from __future__ import annotations

import hashlib
import json
import re
import time
from urllib.parse import quote

from fastapi import Body, HTTPException, Request, Response


def register(app, market, guard):
    store = market.s
    store.x('CREATE TABLE IF NOT EXISTS vault_collections (id INTEGER PRIMARY KEY AUTOINCREMENT, account TEXT NOT NULL, name TEXT NOT NULL, created REAL NOT NULL)')
    store.x('CREATE TABLE IF NOT EXISTS vault_collection_versions (collection INTEGER NOT NULL, version INTEGER NOT NULL, manifest TEXT NOT NULL, sha256 TEXT NOT NULL, created REAL NOT NULL, PRIMARY KEY (collection, version))')

    def owner(request, aid):
        user = guard(request, aid)
        if not user or user.get('account') != aid:
            raise HTTPException(403, 'Sign in as the owner of this vault')

    def owned_file(aid, fid):
        row = store.one('SELECT * FROM files WHERE id=? AND account=?', (fid, aid))
        if not row:
            raise HTTPException(404, 'File not found in this vault')
        return row

    def collection(aid, cid):
        row = store.one('SELECT * FROM vault_collections WHERE id=? AND account=?', (cid, aid))
        if not row:
            raise HTTPException(404, 'Collection not found in this vault')
        return row

    def selected_files(aid, body):
        ids = body.get('files')
        if not isinstance(ids, list) or not ids or len(ids) > 1000 or any(type(fid) is not int or fid <= 0 for fid in ids):
            raise HTTPException(400, 'Select between 1 and 1000 file IDs from your own vault')
        # A collection organizes references; it grants no new permission to sell the files.
        return [owned_file(aid, fid) for fid in sorted(set(ids))]

    def payload(row):
        # Purchased clean is a three-record preview; raw holds the full delivered payload.
        content = row.get('raw')
        if content is None:
            raise HTTPException(409, 'The complete stored payload is unavailable')
        return content.encode('utf-8')

    def file_manifest(row):
        content = payload(row)
        body = json.loads(content)
        origin = re.fullmatch(r'contract (\d+)', row['source'] or '')
        contracts = [int(origin[1])] if origin else []
        if row['source'] == 'licensed resale bundle' and isinstance(body, dict):
            contracts = [cid for cid in body.get('from_contracts', []) if type(cid) is int and cid > 0]
        return {'id': row['id'], 'name': row['name'], 'kind': row['kind'], 'source': row['source'],
                'source_contracts': sorted(set(contracts)), 'sha256': hashlib.sha256(content).hexdigest(),
                'bytes': len(content), 'fingerprints': json.loads(row['fps'] or '[]'),
                'derived_from': json.loads(row['derived_from'] or '[]'),
                'license': {'resale_allowed': bool(row['resale']),
                            'note': 'Existing acquired-data resale permission only; organizing a collection grants no new sale rights.'}}

    def revision(aid, row, files):
        current = store.one('SELECT COALESCE(MAX(version),0) version FROM vault_collection_versions WHERE collection=?', (row['id'],))
        version = current['version'] + 1
        created = time.time()
        manifest = {'schema': 'vault-collection.v1', 'collection': row['id'], 'name': row['name'],
                    'version': version, 'created': created,
                    'note': 'Immutable references to existing vault payloads. File identity, source and resale permissions are preserved.',
                    'files': [file_manifest(f) for f in files]}
        content = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        digest = hashlib.sha256(content.encode('utf-8')).hexdigest()
        store.x('INSERT INTO vault_collection_versions (collection,version,manifest,sha256,created) VALUES (?,?,?,?,?)',
                (row['id'], version, content, digest, created))
        return {'id': row['id'], 'name': row['name'], 'version': version, 'sha256': digest,
                'manifest_url': f'/api/account/{aid}/collections/{row["id"]}/versions/{version}/manifest'}

    def attachment(content, name, digest):
        return Response(content, media_type='application/json', headers={
            'Content-Disposition': "attachment; filename=\"vault-data.json\"; filename*=UTF-8''" + quote(name, safe=''),
            'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff', 'X-Vault-SHA256': digest})

    @app.get('/api/account/{aid}/file/{fid}/download')
    def download(aid: str, fid: int, request: Request):
        owner(request, aid)
        row = owned_file(aid, fid)
        content = payload(row)
        return attachment(content, row['name'] or f'file-{fid}.json', hashlib.sha256(content).hexdigest())

    @app.get('/api/account/{aid}/collections')
    def list_collections(aid: str, request: Request):
        owner(request, aid)
        rows = store.q('SELECT * FROM vault_collections WHERE account=? ORDER BY created DESC,id DESC', (aid,))
        for row in rows:
            row['versions'] = store.q('SELECT version,sha256,created,manifest FROM vault_collection_versions WHERE collection=? ORDER BY version DESC', (row['id'],))
            for version in row['versions']:
                version['files'] = len(json.loads(version.pop('manifest'))['files'])
                version['manifest_url'] = f'/api/account/{aid}/collections/{row["id"]}/versions/{version["version"]}/manifest'
        return {'collections': rows}

    @app.post('/api/account/{aid}/collections')
    def create_collection(aid: str, request: Request, body: dict = Body(...)):
        owner(request, aid)
        name = body.get('name')
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
            raise HTTPException(400, 'Give the collection a name between 1 and 80 characters')
        with store.transaction():
            files = selected_files(aid, body)
            cid = store.insert('vault_collections', account=aid, name=name.strip())
            result = revision(aid, collection(aid, cid), files)
        market.events += 1
        return result

    @app.post('/api/account/{aid}/collections/{cid}/versions')
    def append_version(aid: str, cid: int, request: Request, body: dict = Body(...)):
        owner(request, aid)
        with store.transaction():
            row = collection(aid, cid)
            result = revision(aid, row, selected_files(aid, body))
        market.events += 1
        return result

    @app.get('/api/account/{aid}/collections/{cid}/versions/{version}/manifest')
    def download_manifest(aid: str, cid: int, version: int, request: Request):
        owner(request, aid)
        row = collection(aid, cid)
        saved = store.one('SELECT manifest,sha256 FROM vault_collection_versions WHERE collection=? AND version=?', (cid, version))
        if not saved:
            raise HTTPException(404, 'Collection version not found')
        return attachment(saved['manifest'].encode('utf-8'), f'{row["name"]}-v{version}-manifest.json', saved['sha256'])
