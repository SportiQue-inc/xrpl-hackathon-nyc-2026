"""Explicit package grants freeze complete sanitized records; ordinary escrow owns money and recovery."""
from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, DecimalException

from fastapi import Body, HTTPException, Request

from . import config, data, intake


def register(app, market, guard):
    s = market.s
    s.x('CREATE TABLE IF NOT EXISTS data_packages (id INTEGER PRIMARY KEY AUTOINCREMENT, account TEXT NOT NULL, file INT NOT NULL, collection INT NOT NULL, version INT NOT NULL, name TEXT NOT NULL, price REAL NOT NULL, asset TEXT NOT NULL, unit_micro INT NOT NULL, purpose TEXT NOT NULL, resale INT NOT NULL, sha256 TEXT NOT NULL, kinds TEXT NOT NULL, records INT NOT NULL, created REAL NOT NULL)')

    def owner(request, aid):
        user = guard(request, aid)
        if not user or user.get('account') != aid:
            raise HTTPException(403, 'Sign in as the owner of this vault')
        return user

    def price(value):
        try:
            amount = Decimal(str(value)) * Decimal(1000000) / Decimal(config.MICRO_PER_UNIT)
            if not amount.is_finite() or not 0 < amount < 1000000 or amount != amount.quantize(Decimal('.01')):
                raise ValueError()
            return float(amount)
        except (DecimalException, ValueError):
            raise HTTPException(400, 'Enter a positive price within the settlement precision')

    def summary(row, aid):
        return {'id': row['id'], 'name': row['name'], 'price': float(Decimal(str(row['price'])) * row['unit_micro'] / 1000000),
                'asset': row['asset'], 'purpose': row['purpose'], 'resale': bool(row['resale']),
                'sha256': row['sha256'], 'kinds': json.loads(row['kinds']), 'files': row['file_count'],
                'records': row['records'], 'mine': row['account'] == aid, 'version': row['version']}

    def listing_rows(aid=None):
        return s.q("SELECT p.*, json_array_length(json_extract(f.raw,'$.records')) file_count FROM data_packages p JOIN files f ON f.id=p.file WHERE f.status='listed'" + (' AND p.account=?' if aid else '') + ' ORDER BY p.id DESC', (aid,) if aid else ())

    def source(aid, saved, purpose):
        f = s.one('SELECT * FROM files WHERE id=? AND account=?', (saved['id'], aid))
        if not f or hashlib.sha256((f['raw'] or '').encode()).hexdigest() != saved['sha256']:
            raise HTTPException(409, 'A collection source changed; save a new version before publishing')
        bought = f['status'] in ('bought', 'bundled') or f['source'] == 'licensed resale bundle'
        if f['kind'] == data.PACKAGE_KIND and not bought:
            raise HTTPException(400, 'Choose the original collection sources, or an acquired package with resale permission')
        if bought:
            if not f['resale']:
                raise HTTPException(400, 'Every acquired source needs permission for resale')
            raw = json.loads(f['raw'])
            match = re.fullmatch(r'contract (\d+)', f['source'] or '')
            origins = [int(match[1])] if match else raw.get('from_contracts', []) if f['source'] == 'licensed resale bundle' else []
            if not origins:
                raise HTTPException(400, 'The source purchase receipt is missing')
            purchases = []
            for cid in origins:
                c = s.one("SELECT c.id,c.buyer,c.status,p.resale,p.purpose FROM contracts c JOIN postings p ON p.id=c.posting WHERE c.id=?", (cid,))
                if not c or c['buyer'] != aid or c['status'] != 'settled' or not c['resale']:
                    raise HTTPException(400, 'A settled purchase with resale permission is required')
                if c['purpose'] != purpose:
                    raise HTTPException(400, 'Keep the permitted purpose of every source purchase')
                purchases.append({'contract': c['id'], 'purpose': c['purpose'], 'resale_allowed': True})
            body = {'records': raw['records']}
        else:
            body = json.loads(f['clean'] or '{}')
            att = body.get('_attestation')
            if f['status'] not in ('private', 'listed') or not att or not intake.verify_attestation(att):
                raise HTTPException(400, 'Original sources must pass intake before publishing')
            purchases = []
        if purpose in market.acct(aid)['sell_agent'].get('blocks', []):
            raise HTTPException(400, 'This purpose is blocked by your agent settings')
        return {'kind': f['kind'], 'payload': body, 'source_file': f['id'],
                'source_sha256': saved['sha256'], 'source_contracts': purchases,
                'fingerprints': json.loads(f['fps'] or '[]'),
                'license': {'resale_allowed': bool(f['resale']) if bought else True, 'purpose': purpose}}

    @app.get('/api/account/{aid}/packages')
    def own_packages(aid: str, request: Request):
        owner(request, aid)
        return {'packages': [summary(p, aid) for p in listing_rows(aid)]}

    @app.get('/api/packages')
    def catalog(account: str, request: Request):
        user = owner(request, account)
        return {'packages': [summary(p, account) for p in listing_rows()
                             if not (user.get('demo') and p['account'].startswith('u-'))
                             and not (account.startswith('u-') and p['account'] == 'demo-vault')]}

    @app.post('/api/account/{aid}/packages')
    def publish(aid: str, request: Request, body: dict = Body(...)):
        owner(request, aid)
        if type(body.get('collection')) is not int or type(body.get('version')) is not int:
            raise HTTPException(400, 'Choose a collection version')
        purpose = body.get('purpose')
        if not isinstance(purpose, str) or not 1 <= len(purpose.strip()) <= 160 or type(body.get('resale')) is not bool:
            raise HTTPException(400, 'Set a permitted purpose and an explicit resale choice')
        purpose = purpose.strip()
        asking = price(body.get('price'))
        with market.lock, s.transaction():
            v = s.one('SELECT v.*,c.name FROM vault_collection_versions v JOIN vault_collections c ON c.id=v.collection WHERE c.account=? AND c.id=? AND v.version=?', (aid, body['collection'], body['version']))
            if not v:
                raise HTTPException(404, 'Collection version not found in this vault')
            records = [source(aid, f, purpose) for f in json.loads(v['manifest'])['files']]
            fps = set()
            for r in records:
                if fps.intersection(r['fingerprints']):
                    raise HTTPException(400, 'Collection sources contain overlapping original records; remove duplicates before publishing')
                fps.update(r['fingerprints'])
            if not fps:
                raise HTTPException(400, 'Package sources need verified record identities')
            snapshot = {'_people': 1, 'records': records,
                        '_package': {'schema': 'vault-package.v1', 'collection': v['collection'], 'version': v['version'],
                                     'collection_sha256': v['sha256'], 'purpose': purpose, 'resale_allowed': body['resale']}}
            snapshot['_attestation'] = intake.attest(data.PACKAGE_KIND, snapshot, ['complete sanitized sources', 'source resale grants', 'original record identities retained'], False)
            content = data.dumps(snapshot)
            digest = hashlib.sha256(content.encode()).hexdigest()
            fid = s.insert('files', account=aid, kind=data.PACKAGE_KIND, name=v['name'] + '.json', raw=content, clean=content,
                           status='listed', fps=sorted(fps), source='licensed mixed package', resale=int(body['resale']),
                           derived_from=[f['source_file'] for f in records], bytes=len(content.encode()))
            pid = s.insert('data_packages', account=aid, file=fid, collection=v['collection'], version=v['version'], name=v['name'],
                           price=asking, asset=market.rail.symbol(), unit_micro=config.MICRO_PER_UNIT, purpose=purpose,
                           resale=int(body['resale']), sha256=digest, kinds=sorted({r['kind'] for r in records}), records=len(fps))
        market.events += 1
        return summary(next(p for p in listing_rows(aid) if p['id'] == pid), aid)

    @app.post('/api/account/{aid}/packages/{pid}/buy')
    def buy(aid: str, pid: int, request: Request, body: dict = Body(...)):
        user = owner(request, aid)
        maximum = price(body.get('price'))
        with market.lock:
            row = s.one("SELECT p.*,f.raw,f.clean,f.fps,f.status FROM data_packages p JOIN files f ON f.id=p.file WHERE p.id=?", (pid,))
            if not row or row['status'] != 'listed':
                raise HTTPException(404, 'Package not available')
            if row['account'] == aid or (user.get('demo') and row['account'].startswith('u-')) or (aid.startswith('u-') and row['account'] == 'demo-vault'):
                raise HTTPException(403, 'This package is not available to this account')
            if body.get('sha256') != row['sha256'] or body.get('purpose') != row['purpose'] or type(body.get('resale')) is not bool or (body['resale'] and not row['resale']):
                raise HTTPException(409, 'Review the exact package contents, permitted purpose and resale terms')
            if row['asset'] != market.rail.symbol() or row['unit_micro'] != config.MICRO_PER_UNIT:
                raise HTTPException(409, 'Package is priced in a different asset; its owner must publish a new listing')
            if hashlib.sha256(row['clean'].encode()).hexdigest() != row['sha256']:
                raise HTTPException(409, 'Package snapshot changed; purchase refused')
            if aid not in market.addr or row['account'] not in market.addr:
                raise HTTPException(409, 'Wait for both agent wallets to connect')
            p = s.insert('postings', buyer=aid, kind=data.PACKAGE_KIND, offer=maximum, max=maximum,
                         purpose=row['purpose'], lot=1, min_trust=.7, resale=int(body['resale']), status='package', once=1)
            trace = {'protocol': [], 'tx': [], 'model': 'rules', 'package': {'id': pid, 'sha256': row['sha256']}}
            cid = s.insert('contracts', posting=p, buyer=aid, seller=row['account'], kind=data.PACKAGE_KIND,
                           status='negotiating', asset=row['asset'], unit_micro=row['unit_micro'], sellers=[row['account']],
                           overview={'name': row['name'], 'files': 1, 'records': row['records'], 'fields': [], 'start': None, 'end': None}, trace=trace)
            def say(who, side, text):
                s.insert('messages', contract=cid, speaker=who, side=side, text=text,
                         thinking={'t': 'Explicit package price and permitted terms; deterministic checks before payment.', 'by': 'rules'})
            say(aid, 'buyer', f'I offer up to {maximum * config.MICRO_PER_UNIT / 1e6:g} {row["asset"]} for {row["name"]}, for {row["purpose"]}.')
            say(row['account'], 'seller', f'This complete package costs {row["price"] * row["unit_micro"] / 1e6:g} {row["asset"]}; resale is {"allowed" if row["resale"] else "not allowed"}.')
            reason = None
            if maximum < row['price']:
                reason = 'The package price exceeds the buyer budget; no payment.'
            elif market.owned_fps(aid, data.PACKAGE_KIND) & set(json.loads(row['fps'])):
                reason = 'The buyer already owns some of these records; the complete package is refused before payment.'
            elif market.balance(aid) is None or market.balance(aid) < row['price'] * config.MICRO_PER_UNIT / 1e6 + (0 if market.rail.token else .2):
                reason = 'Insufficient balance for this package; no payment.'
            att = json.loads(row['clean']).get('_attestation', {})
            if not intake.verify_attestation(att):
                reason = 'Package intake signature is invalid; no payment.'
            if reason:
                say(aid, 'buyer', reason)
                s.x("UPDATE contracts SET status='rejected',reason=? WHERE id=?", (reason, cid))
                s.x("UPDATE postings SET status='rejected' WHERE id=?", (p,))
            else:
                say(aid, 'buyer', 'I accept these exact contents, price and permitted terms. Starting conditional payment and encrypted delivery.')
                f = s.one('SELECT * FROM files WHERE id=?', (row['file'],))
                market.settle(cid, s.one('SELECT * FROM postings WHERE id=?', (p,)), [(row['account'], [f], row['price'])], trace, row['price'])
            market.events += 1
            c = s.one('SELECT status,reason FROM contracts WHERE id=?', (cid,))
            return {'contract': cid, **c}
