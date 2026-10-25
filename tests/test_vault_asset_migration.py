"""Currency migration preserves explicit assets and repairs only proof-bound AP4M labels."""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'prototypes/data-vault-market/server'))
from vaultmarket.store import SCHEMA, Store

EVM_HASH = '0x' + 'ab' * 32
FORWARD_HASH = '0x' + 'cd' * 32


def proof(**changes):
    return {'verified': True, 'voucher_redeemed_tx': EVM_HASH, 'amount_rlusd': '0.054321',
            'claim_id': '0x' + '12' * 32, 'voucher_url': 'https://explorer.testnet.xrplevm.org/tx/' + EVM_HASH,
            'forward_tx': FORWARD_HASH, **changes}


def trace(p):
    return {'tx': [{'seller': 'synthetic-seller', 'ap4m': [p]}]}


def non_currency_snapshot(store):
    return {table: [{k: v for k, v in row.items() if k != 'asset'} for row in store.q(f'SELECT * FROM {table} ORDER BY id')]
            for table in ('contracts', 'txs', 'files')}


def test_reopening_preserves_explicit_currency_and_only_fills_missing_values(tmp_path):
    path = str(tmp_path / 'preserved.db')
    s = Store(path)
    xrp = s.insert('contracts', asset='XRP', total=38, unit_micro=10000)
    usd = s.insert('contracts', asset='test USD', total=7.25, unit_micro=1000000)
    rows = [
        ('EscrowFinish (key released)', 'A' * 64, xrp, 'XRP'),
        ('EscrowFinish (key released)', 'B' * 64, usd, 'test USD'),
        ('Payment', 'C' * 64, usd, 'XRP'),
        ('Payment', 'D' * 64, xrp, 'test USD'),
        ('AP4M VoucherRedeemed', EVM_HASH, usd, 'RLUSD (AP4M)'),
        ('Payment', 'E' * 64, xrp, 'Other issued asset'),
        ('Payment', 'F' * 64, usd, None),
        ('Payment', '1' * 64, xrp, ''),
        ('Payment', '2' * 64, None, None),
    ]
    for kind, tx_hash, cid, asset in rows:
        s.insert('txs', contract=cid, type=kind, hash=tx_hash, asset=asset, drops=123456,
                 src='synthetic-sender', dst='synthetic-recipient', result='tesSUCCESS')
    before = non_currency_snapshot(s)
    s.db.close(); s = Store(path)
    assert [row['asset'] for row in s.q('SELECT asset FROM txs ORDER BY id')] == [
        'XRP', 'test USD', 'XRP', 'test USD', 'RLUSD (AP4M)', 'Other issued asset', 'test USD', 'XRP', 'XRP']
    assert non_currency_snapshot(s) == before
    snapshot = s.q('SELECT * FROM txs ORDER BY id')
    s.db.close()
    assert Store(path).q('SELECT * FROM txs ORDER BY id') == snapshot


def test_verified_hash_amount_claim_url_proof_repairs_only_bound_rows(tmp_path):
    path = str(tmp_path / 'repair.db')
    s = Store(path)
    cid = s.insert('contracts', asset='test USD', total=2, unit_micro=1, trace=trace(proof()))
    cases = [
        (cid, 'AP4M VoucherRedeemed', EVM_HASH, 'test USD', 54321, 'RLUSD (AP4M)'),
        (cid, 'RLUSD forward to seller', FORWARD_HASH, 'test USD', 54321, 'RLUSD (AP4M)'),
        (cid, 'RLUSD forward to seller', FORWARD_HASH, 'XRP', 54322, 'XRP'),
        (None, 'AP4M VoucherRedeemed (cleaning fee)', EVM_HASH, 'XRP', 54321, 'XRP'),
        (cid, 'AP4M VoucherRedeemed (cleaning fee)', EVM_HASH, 'test USD', 54321, 'test USD'),
        (cid, 'Payment', EVM_HASH, 'XRP', 54321, 'XRP'),
        (cid, 'AP4M VoucherRedeemed', '0x' + 'ef' * 32, 'XRP', 54321, 'XRP'),
    ]
    for contract, kind, tx_hash, asset, drops, _ in cases:
        s.insert('txs', contract=contract, type=kind, hash=tx_hash, asset=asset, result='verified',
                 drops=drops, src='synthetic-seller', dst='synthetic-buyer')
    s.insert('files', account='synthetic-buyer', name='preserved.json', raw='{"records":[1,2,3]}',
             clean='{"records":[1]}', fps=['same-fingerprint'], source='contract 1', resale=1)
    before = non_currency_snapshot(s)
    s.db.close(); s = Store(path)
    assert [row['asset'] for row in s.q('SELECT asset FROM txs ORDER BY id')] == [case[-1] for case in cases]
    assert s.one('SELECT asset FROM contracts WHERE id=?', (cid,))['asset'] == 'RLUSD (AP4M)'
    assert non_currency_snapshot(s) == before
    once = {table: s.q(f'SELECT * FROM {table} ORDER BY id') for table in ('contracts', 'txs', 'files')}
    s.db.close(); reopened = Store(path)
    assert {table: reopened.q(f'SELECT * FROM {table} ORDER BY id') for table in once} == once


@pytest.mark.parametrize('change', [
    None, {'verified': False}, {'verified': 1}, {'amount_rlusd': '0.054322'}, {'amount_rlusd': 'NaN'},
    {'amount_rlusd': '1e999999999'}, {'amount_rlusd': '-0.054321'},
    {'amount_rlusd': '0'}, {'amount_rlusd': '0.100001'},
    {'amount_rlusd': '0.054321000000000000000000000000000001'},
    {'voucher_redeemed_tx': '0x' + 'ef' * 32}, {'claim_id': ''}, {'claim_id': 'malformed-claim'},
    {'voucher_url': 'https://other.example/tx/' + EVM_HASH}, {'voucher_url': None},
])
def test_missing_or_mismatched_proof_does_not_relabel_existing_receipts(tmp_path, change):
    path = str(tmp_path / 'unproven.db')
    s = Store(path)
    cid = s.insert('contracts', asset='test USD', total=2, unit_micro=1,
                   trace={} if change is None else trace(proof(**change)))
    s.insert('txs', contract=cid, type='AP4M VoucherRedeemed', hash=EVM_HASH,
             asset='test USD', drops=54321, result='verified')
    s.insert('txs', contract=cid, type='RLUSD forward to seller', hash=FORWARD_HASH,
             asset='XRP', drops=54321, result='ok')
    before = {table: s.q(f'SELECT * FROM {table}') for table in ('contracts', 'txs')}
    s.db.close(); reopened = Store(path)
    assert {table: reopened.q(f'SELECT * FROM {table}') for table in before} == before


def test_native_coexistence_and_arbitrary_explicit_assets_are_preserved(tmp_path):
    path = str(tmp_path / 'native.db')
    s = Store(path)
    native = s.insert('contracts', asset='XRP', trace=trace(proof()))
    other = s.insert('contracts', asset='Other issued asset', trace=trace(proof()))
    for cid in (native, other):
        s.insert('txs', contract=cid, type='AP4M VoucherRedeemed', hash=EVM_HASH, asset='Other issued asset' if cid == other else 'test USD', drops=54321, result='verified')
    s.insert('txs', contract=native, type='EscrowCreate', hash='A' * 64, asset='XRP', drops=12345)
    before = {table: s.q(f'SELECT * FROM {table}') for table in ('contracts', 'txs')}
    s.db.close(); reopened = Store(path)
    assert {table: reopened.q(f'SELECT * FROM {table}') for table in before} == before


def test_legacy_database_without_transaction_asset_inherits_the_contract_once(tmp_path):
    path = str(tmp_path / 'legacy.db')
    db = sqlite3.connect(path); db.executescript(SCHEMA)
    db.execute('ALTER TABLE contracts ADD COLUMN asset TEXT')
    db.execute("INSERT INTO contracts (id,asset,total) VALUES (1,'test USD',7.3),(2,'XRP',38),(3,NULL,2)")
    db.execute("INSERT INTO txs (id,contract,type,hash,drops) VALUES (1,1,'EscrowFinish','A',7300000),(2,2,'EscrowFinish','B',380000),(3,3,'EscrowCreate','C',20000),(4,NULL,'Payment','D',10000)")
    db.commit(); db.close(); s = Store(path)
    assert [row['asset'] for row in s.q('SELECT asset FROM txs ORDER BY id')] == ['test USD', 'XRP', 'XRP', 'XRP']
    assert [row['unit_micro'] for row in s.q('SELECT unit_micro FROM contracts ORDER BY id')] == [1000000, 10000, 10000]
    before = s.q('SELECT * FROM txs ORDER BY id')
    s.db.close()
    assert Store(path).q('SELECT * FROM txs ORDER BY id') == before


@pytest.mark.parametrize('result', ['failed', 'redeemed', None])
def test_unverified_recorded_result_cannot_repair_even_a_verified_trace(tmp_path, result):
    path = str(tmp_path / 'failed-result.db')
    s = Store(path)
    cid = s.insert('contracts', asset='test USD', trace=trace(proof()))
    s.insert('txs', contract=cid, type='AP4M VoucherRedeemed', hash=EVM_HASH,
             asset='test USD', drops=54321, result=result)
    before = {table: s.q(f'SELECT * FROM {table}') for table in ('contracts', 'txs')}
    s.db.close(); reopened = Store(path)
    assert {table: reopened.q(f'SELECT * FROM {table}') for table in before} == before
