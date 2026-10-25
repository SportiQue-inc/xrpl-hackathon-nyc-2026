"""Requests, one-to-one trades and recovery use the real store and mock ledger."""
import json
import os
import random
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prototypes/data-vault-market/server"))
os.environ.setdefault("VM_DATA_DIR", tempfile.mkdtemp(prefix="vault-tests-"))
from vaultmarket import config, data, rail
from vaultmarket.market import Market


@pytest.fixture
def market(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LEDGER", "mock")
    monkeypatch.setattr(config, "LLM_PROVIDER", "none")
    monkeypatch.setattr(config, "ASSET", "XRP")
    monkeypatch.setattr(config, "MICRO_PER_UNIT", 10000)
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "market.db"))
    monkeypatch.setattr(rail, "KEYS_FILE", str(tmp_path / "keys.json"))
    m = Market()
    for aid, typ in (("buyer", "org"), ("seller", "person")):
        m.s.insert("accounts", id=aid, name=aid, type=typ, trust=.95, verified=1,
                   sell_agent={"mode": "ask", "min": {"sleep_log": 7}, "blocks": ["insurance pricing"]},
                   buy_agent={"auto_limit": 100, "min_trust": .7, "max_overlap": .3})
        m.addr[aid] = m.rail.ensure_account(aid)
    body = data.make_record("sleep_log", random.Random(1), "Synthetic", 0, (0, 0))
    m.test_file = m.add_file("seller", "sleep_log", "sleep.json", body, listed=False, source="synthetic")
    m.test_post = m.s.insert("postings", buyer="buyer", kind="sleep_log", offer=8, max=20,
                           purpose="sleep research", lot=5, min_trust=.7, status="open", once=1)
    return m


def journal(m, state="open", finished=False):
    from agentrail.ledger.conditions import condition_hex, new_key
    key = new_key()
    cid = m.s.insert("contracts", posting=m.test_post, buyer="buyer", kind="sleep_log", status="settling", trace={"protocol": [], "tx": []})
    p = m.rail.led.prepare_escrow_create(m.addr["buyer"], m.addr["seller"], 80000,
                                      condition_hex(key), m.rail.led.now() + 3600, f"vaultmarket/contract/{cid}")
    m.rail._submit(p)
    seq = m.rail._seq_of(p)
    fh = m.rail.finish_escrow(m.addr["seller"], m.addr["buyer"], seq, key, f"vaultmarket/contract/{cid}")["hash"] if finished else None
    m.s.insert("escrows", contract=cid, buyer="buyer", seller="seller", owner=m.addr["buyer"], seq=seq,
               create_hash=p.tx_hash, finish_hash=fh if state == "finished" else None, k=key.hex(),
               cancel_after=m.rail.led.now() + 3600, drops=80000, price=8, files=[m.test_file], state=state)
    return cid


def test_recovery_preserves_the_actual_file_record(market):
    cid = journal(market)
    expected = json.loads(market.s.one("SELECT clean FROM files WHERE id=?", (market.test_file,))["clean"])
    market.recover()
    assert market.s.one("SELECT status FROM contracts WHERE id=?", (cid,))["status"] == "settled"
    bought = market.s.one("SELECT raw FROM files WHERE source=?", (f"contract {cid}",))
    assert json.loads(bought["raw"])["records"] == [expected]


def test_recovery_keeps_the_purchased_resale_permission(market):
    market.s.x("UPDATE postings SET resale=1 WHERE id=?", (market.test_post,))
    cid = journal(market)
    market.recover()
    assert market.s.one("SELECT resale FROM files WHERE source=?", (f"contract {cid}",))["resale"] == 1


def test_recovery_closes_a_contract_with_all_legs_finished_before_crash(market):
    cid = journal(market, state="finished", finished=True)
    market.recover()
    assert market.s.one("SELECT status FROM contracts WHERE id=?", (cid,))["status"] == "settled"


def test_recovery_recognizes_finish_validated_before_database_write(market):
    cid = journal(market, finished=True)
    market.recover()
    assert market.s.one("SELECT status FROM contracts WHERE id=?", (cid,))["status"] == "settled"
    assert market.s.one("SELECT state FROM escrows WHERE contract=?", (cid,))["state"] == "finished"


def test_recovery_is_idempotent(market):
    cid = journal(market)
    market.recover()
    market.recover()
    assert market.s.one("SELECT count(*) n FROM files WHERE source=?", (f"contract {cid}",))["n"] == 1
    assert market.s.stat("settled") == 1


def test_sell_button_and_chat_both_create_durable_requests(market, monkeypatch):
    from fastapi.testclient import TestClient
    from vaultmarket import app as web
    monkeypatch.setattr(web, "M", market)
    monkeypatch.setattr(config, "PUBLIC", False)
    c = TestClient(web.app)
    assert c.post(f"/api/account/seller/sell-now/{market.test_post}").status_code == 200
    account = c.get("/api/account/seller").json()
    assert account.get("agent_queue"), "A sale must be persisted and visible beside the agent"
    assert account["agent_queue"][0]["status"] == "queued"
    assert account["chat"][-1]["role"] == "agent"
    assert c.post("/api/account/seller/chat", json={"text": "sell my sleep logs"}).status_code == 200
    assert len(c.get("/api/account/seller").json()["agent_queue"]) == 1, "Repeated instructions must not duplicate an active sale"


def test_one_seller_can_trade_without_an_unrequested_group_vote(market):
    market.s.x("UPDATE files SET status='listed' WHERE id=?", (market.test_file,))
    market.s.insert("interests", account="seller", posting=market.test_post)
    cid = market.negotiate(market.s.one("SELECT * FROM postings WHERE id=?", (market.test_post,)))
    c = market.s.one("SELECT * FROM contracts WHERE id=?", (cid,))
    assert c["status"] == "settled", (c["reason"], c["trace"])
    assert json.loads(c["sellers"]) == ["seller"]


def test_public_demo_cannot_modify_somebody_elses_vault(market, monkeypatch):
    from fastapi.testclient import TestClient
    from vaultmarket import app as web
    monkeypatch.setattr(web, "M", market)
    monkeypatch.setattr(config, "PUBLIC", True)
    assert TestClient(web.app).post(f"/api/account/seller/sell-now/{market.test_post}").status_code == 403


def test_all_finished_recovery_also_restores_receipt_links(market):
    cid = journal(market, state="finished", finished=True)
    market.recover()
    assert len(market.s.q("SELECT * FROM txs WHERE contract=?", (cid,))) == 2


def test_sale_queue_is_actually_processed_one_to_one(market):
    q = market.enqueue_sale("seller", "sleep_log", market.test_post)
    assert market.process_sale_queue()
    q = market.s.one("SELECT * FROM sale_queue WHERE id=?", (q["id"],))
    assert q["status"] == "settled"
    assert json.loads(market.s.one("SELECT sellers FROM contracts WHERE id=?", (q["contract"],))["sellers"]) == ["seller"]


def test_blocked_sale_keeps_the_file_private(market):
    market.s.x("UPDATE postings SET purpose='insurance pricing' WHERE id=?", (market.test_post,))
    q = market.enqueue_sale("seller", "sleep_log", market.test_post)
    assert q["status"] == "blocked"
    assert market.s.one("SELECT status FROM files WHERE id=?", (market.test_file,))["status"] == "private"


def test_old_xrp_history_uses_paid_amount_not_current_usd_conversion(market, monkeypatch):
    from fastapi.testclient import TestClient
    from vaultmarket import app as web
    monkeypatch.setattr(web, "M", market)
    cid = market.s.insert("contracts", posting=market.test_post, buyer="buyer", kind="sleep_log", status="settled", total=13.7, sellers=["seller"], asset="XRP", unit_micro=10000)
    market.s.insert("txs", contract=cid, type="EscrowFinish (key released)", drops=137000, result="tesSUCCESS", src="seller", dst="buyer", asset="XRP")
    c = TestClient(web.app).get("/api/market").json()["contracts"][0]
    assert (c["drops"], c["asset"]) == (137000, "XRP")


def test_crash_during_accounting_cannot_duplicate_delivery_or_proceeds(market, monkeypatch):
    market.s.x("UPDATE files SET status='listed' WHERE id=?", (market.test_file,))
    market.s.insert("interests", account="seller", posting=market.test_post)
    real_bump = market.s.bump
    def crash(k, by=1):
        if k == "settled":
            raise RuntimeError("simulated process stop during accounting")
        return real_bump(k, by)
    monkeypatch.setattr(market.s, "bump", crash)
    with pytest.raises(RuntimeError):
        market.negotiate(market.s.one("SELECT * FROM postings WHERE id=?", (market.test_post,)))
    assert market.s.one("SELECT status FROM contracts ORDER BY id DESC LIMIT 1")["status"] == "settling"
    monkeypatch.setattr(market.s, "bump", real_bump)
    market.recover()
    market.recover()
    assert market.s.one("SELECT sold FROM files WHERE id=?", (market.test_file,))["sold"] == 1
    assert market.s.one("SELECT count(*) n FROM files WHERE status='bought'")["n"] == 1
    assert market.s.stat("settled") == 1


def test_a_created_but_unfinished_escrow_stays_recoverable(market, monkeypatch):
    market.s.x("UPDATE files SET status='listed' WHERE id=?", (market.test_file,))
    market.s.insert('interests',account='seller',posting=market.test_post)
    original=market.rail.finish_escrow
    monkeypatch.setattr(market.rail,'finish_escrow',lambda *a,**kw:{'ok':False,'hash':None,'result':'unknown'})
    cid=market.negotiate(market.s.one('SELECT * FROM postings WHERE id=?',(market.test_post,)))
    assert market.s.one('SELECT status FROM contracts WHERE id=?',(cid,))['status']=='settling'
    monkeypatch.setattr(market.rail,'finish_escrow',original)
    market.recover()
    assert market.s.one('SELECT status FROM contracts WHERE id=?',(cid,))['status']=='settled'


def test_expired_escrow_with_saved_key_is_refunded_only_after_expiry(market):
    cid=journal(market)
    market.rail.led.clock+=3601
    market.recover()
    e=market.s.one('SELECT * FROM escrows WHERE contract=?',(cid,))
    assert e['state']=='refunded'
    assert market.rail.receipt(e['finish_hash'])['type']=='EscrowCancel'
    assert market.rail.receipt(e['finish_hash'])['destination']==market.addr['buyer']


def test_existing_test_usd_and_xrp_keep_distinct_units_after_migration(market):
    from vaultmarket.store import Store
    a=market.s.insert('contracts',kind='sleep_log',asset='test USD',status='settled')
    b=market.s.insert('contracts',kind='sleep_log',asset=None,status='settled')
    market.s.insert('txs',contract=a,type='EscrowFinish',drops=2900000,result='tesSUCCESS')
    market.s.x("ALTER TABLE contracts DROP COLUMN unit_micro")
    market.s.db.close()
    s=Store(config.DB_PATH)
    assert s.one('SELECT asset,unit_micro FROM contracts WHERE id=?',(a,))=={'asset':'test USD','unit_micro':1000000}
    assert s.one('SELECT asset,unit_micro FROM contracts WHERE id=?',(b,))=={'asset':'XRP','unit_micro':10000}
    assert s.one('SELECT asset FROM txs WHERE contract=?',(a,))['asset']=='test USD'


def test_data_overview_uses_the_transferred_records_without_owner_identifiers(market):
    market.s.x("UPDATE files SET status='listed' WHERE id=?",(market.test_file,))
    market.s.insert('interests',account='seller',posting=market.test_post)
    cid=market.negotiate(market.s.one('SELECT * FROM postings WHERE id=?',(market.test_post,)))
    d=json.loads(market.s.one('SELECT overview FROM contracts WHERE id=?',(cid,))['overview'])
    assert d['files']==1 and d['records']==7 and d['start']=='2026-09-01' and d['end']=='2026-09-07'
    assert 'total_h' in d['fields']
    assert 'owner_name' not in d['fields'] and 'email' not in d['fields']


def test_restart_resubmits_the_same_saved_create_intent(market):
    from agentrail.ledger.conditions import condition_hex,new_key
    key=new_key();cid=market.s.insert('contracts',posting=market.test_post,buyer='buyer',kind='sleep_log',status='settling',sellers=['seller'])
    p=market.rail.led.prepare_escrow_create(market.addr['buyer'],market.addr['seller'],80000,condition_hex(key),market.rail.led.now()+3600,f'vaultmarket/contract/{cid}')
    market.s.insert('escrows',contract=cid,buyer='buyer',seller='seller',owner=market.addr['buyer'],seq=market.rail._seq_of(p),create_hash=p.tx_hash,create_blob=p.blob,k=key.hex(),cancel_after=market.rail.led.now()+3600,drops=80000,price=8,files=[market.test_file],state='open')
    market.recover()
    market.recover()
    assert market.s.one('SELECT status FROM contracts WHERE id=?',(cid,))['status']=='settled'
    assert len([t for t in market.rail.led.txs.values() if t.get('TransactionType')=='EscrowCreate'])==1


def test_buyer_approval_survives_market_process_restart(market):
    market.s.x("UPDATE accounts SET type='person',buy_agent=? WHERE id='buyer'",(json.dumps({'auto_limit':1,'max_overlap':.3,'min_trust':.7}),))
    market.s.x("UPDATE files SET status='listed' WHERE id=?",(market.test_file,))
    market.s.insert('interests',account='seller',posting=market.test_post)
    cid=market.negotiate(market.s.one('SELECT * FROM postings WHERE id=?',(market.test_post,)))
    assert market.s.one('SELECT status FROM contracts WHERE id=?',(cid,))['status']=='awaiting buyer'
    resumed=Market();resumed.rail=market.rail;resumed.addr=market.addr
    assert resumed.approve_buy(cid)
    assert resumed.s.one('SELECT status FROM contracts WHERE id=?',(cid,))['status']=='settled'
    assert not resumed.approve_buy(cid)


def test_even_a_small_overlap_in_a_resale_bundle_never_charges_twice(market):
    original=market.s.one('SELECT * FROM files WHERE id=?',(market.test_file,))
    market.s.insert('files',account='buyer',kind='sleep_log',status='bought',fps=['record-X'],raw={},clean={},resale=1)
    market.s.x('UPDATE files SET fps=?,status=\'listed\' WHERE id=?',(json.dumps(['record-X']+['new-'+str(i) for i in range(20)]),market.test_file))
    market.s.insert('interests',account='seller',posting=market.test_post)
    cid=market.negotiate(market.s.one('SELECT * FROM postings WHERE id=?',(market.test_post,)),seller_id='seller')
    c=market.s.one('SELECT * FROM contracts WHERE id=?',(cid,))
    assert c['status']=='rejected' and 'already own' in c['reason'].lower()
    assert not market.s.q('SELECT * FROM escrows')


def test_resale_bundle_keeps_lineage_and_requires_resale_rights(market):
    f=market.s.one('SELECT * FROM files WHERE id=?',(market.test_file,))
    market.s.x("UPDATE files SET status='bought',resale=1 WHERE id=?",(market.test_file,))
    market.s.x('UPDATE files SET raw=? WHERE id=?',(data.dumps({'from_contract':123,'_people':1,'records':[json.loads(f['clean'])]}),market.test_file))
    bid=market.bundle_files('seller',[market.test_file])
    b=market.s.one('SELECT * FROM files WHERE id=?',(bid,))
    assert set(json.loads(b['fps']))==set(json.loads(f['fps']))
    assert json.loads(b['derived_from'])==[market.test_file]
    assert json.loads(b['raw'])['from_contracts']==[123]
    with pytest.raises(ValueError,match='resale'):
        market.bundle_files('buyer',[market.test_file])


def test_changed_file_name_and_supplied_fingerprints_cannot_hide_the_same_records(market):
    f=market.s.one('SELECT raw FROM files WHERE id=?',(market.test_file,))
    body=json.loads(f['raw']);body['_fps']=['a-new-client-claim'];body['owner_name']='Renamed seller'
    copy=market.add_file('seller','sleep_log','renamed.csv',body,listed=True,source='synthetic')
    assert market.owned_fps('seller','sleep_log') == set(json.loads(market.s.one('SELECT fps FROM files WHERE id=?',(copy,))['fps']))


def test_agent_finds_sellable_data_from_my_db_before_asking_what_to_sell(market,monkeypatch):
    from fastapi.testclient import TestClient
    from vaultmarket import app as web
    monkeypatch.setattr(web,'M',market);monkeypatch.setattr(config,'PUBLIC',False)
    c=TestClient(web.app)
    assert c.post('/api/account/seller/chat',json={'text':'뭘 팔 수 있어?'}).status_code==200
    msg=c.get('/api/account/seller').json()['chat'][-1]
    assert msg['actions'] and msg['actions'][0]['posting']==market.test_post
    assert 'sleep' in msg['text'].lower()
    assert market.s.one('SELECT status FROM files WHERE id=?',(market.test_file,))['status']=='private'


def test_a_to_b_then_a_to_c_to_b_cannot_resell_the_same_record(market):
    market.s.x("UPDATE files SET status='listed' WHERE id=?",(market.test_file,))
    market.s.x('UPDATE postings SET resale=1 WHERE id=?',(market.test_post,))
    market.s.insert('interests',account='seller',posting=market.test_post)
    assert market.s.one('SELECT status FROM contracts WHERE id=?',(market.negotiate(market.s.one('SELECT * FROM postings WHERE id=?',(market.test_post,)),seller_id='seller'),))['status']=='settled'
    market.s.insert('accounts',id='reseller',name='C',type='org',trust=.95,verified=1,sell_agent={'mode':'auto','min':{'sleep_log':7},'blocks':[]},buy_agent={'auto_limit':100,'max_overlap':.3,'min_trust':.7})
    market.addr['reseller']=market.rail.ensure_account('reseller')
    p=market.s.insert('postings',buyer='reseller',kind='sleep_log',offer=8,max=20,purpose='aggregation and resale',lot=1,min_trust=.7,status='open',resale=1,once=1)
    market.s.insert('interests',account='seller',posting=p)
    market.negotiate(market.s.one('SELECT * FROM postings WHERE id=?',(p,)),seller_id='seller')
    f=market.s.one("SELECT id FROM files WHERE account='reseller' AND status='bought'")
    bid=market.bundle_files('reseller',[f['id']]);market.s.x('UPDATE files SET name=\'a new marketing name.json\' WHERE id=?',(bid,))
    p=market.s.insert('postings',buyer='buyer',kind='sleep_log',offer=8,max=20,purpose='sleep research',lot=1,min_trust=.7,status='open',once=1)
    cid=market.negotiate(market.s.one('SELECT * FROM postings WHERE id=?',(p,)),seller_id='reseller')
    c=market.s.one('SELECT status,reason FROM contracts WHERE id=?',(cid,))
    assert c['status']=='rejected' and 'already own' in c['reason']
    assert not market.s.q('SELECT * FROM escrows WHERE contract=?',(cid,))


def test_two_pending_approvals_cannot_buy_the_same_records_twice(market):
    market.s.x("UPDATE accounts SET type='person',buy_agent=? WHERE id='buyer'",(json.dumps({'auto_limit':1,'max_overlap':.3,'min_trust':.7}),))
    market.s.x("UPDATE files SET status='listed' WHERE id=?",(market.test_file,))
    market.s.insert('interests',account='seller',posting=market.test_post)
    w=market.s.one('SELECT * FROM postings WHERE id=?',(market.test_post,))
    a=market.negotiate(w,seller_id='seller');b=market.negotiate(w,seller_id='seller')
    assert market.approve_buy(a)
    assert not market.approve_buy(b)
    assert market.s.one("SELECT count(*) n FROM contracts WHERE status='settled'")['n']==1


@pytest.mark.parametrize('declared,delivered,expected',[("100000000","2000000","2"),({'currency':'USD','issuer':'rOther','value':'100'},{'currency':'USD','issuer':'rOther','value':'2'},'2')])
def test_payment_receipts_use_actual_delivery_not_the_requested_maximum(market,declared,delivered,expected):
    result={'validated':True,'tx_json':{'TransactionType':'Payment','DeliverMax':declared,'Amount':declared,'Account':'source','Destination':'dest','Flags':131072},'meta':{'TransactionResult':'tesSUCCESS','delivered_amount':delivered}}
    assert market.rail.receipt('test',result)['gross_amount']==expected


def test_unavailable_payment_delivery_is_never_counted_as_a_payout(market):
    r={'validated':True,'tx_json':{'TransactionType':'Payment','Amount':'100000000','Flags':131072},'meta':{'TransactionResult':'tesSUCCESS','delivered_amount':'unavailable'}}
    assert market.rail.receipt('test',r)['gross_amount'] is None


def test_another_issuer_token_is_not_labeled_as_our_test_usd(market):
    from types import SimpleNamespace
    market.rail.name='testnet';market.rail.issuer='rConfigured'
    market.rail.led.client=SimpleNamespace(request=lambda _:SimpleNamespace(result={'transactions':[{'hash':'H','validated':True,'tx_json':{'TransactionType':'Payment','Account':'source','Destination':'dest','Amount':{'currency':'USD','issuer':'rOther','value':'2'}},'meta':{'TransactionResult':'tesSUCCESS','delivered_amount':{'currency':'USD','issuer':'rOther','value':'2'}}}]}))
    row=market.rail.wallet_activity('dest')[0]
    assert row['asset']!='test USD' and 'rOther' in row['asset']


def test_chat_sale_minimum_is_in_actual_asset_units(market,monkeypatch):
    from fastapi.testclient import TestClient
    from vaultmarket import app as web
    monkeypatch.setattr(web,'M',market);monkeypatch.setattr(config,'PUBLIC',False)
    assert TestClient(web.app).post('/api/account/seller/chat',json={'text':'sell my sleep logs minimum 0.12 XRP'}).status_code==200
    assert market.acct('seller')['sell_agent']['min']['sleep_log']==12


def test_chat_purchase_price_is_in_actual_asset_units(market,monkeypatch):
    from fastapi.testclient import TestClient
    from vaultmarket import app as web
    from types import SimpleNamespace
    monkeypatch.setattr(web,'M',market);monkeypatch.setattr(config,'PUBLIC',False)
    monkeypatch.setattr(web.threading,'Thread',lambda **kw:SimpleNamespace(start=lambda:None))
    assert TestClient(web.app).post('/api/account/seller/chat',json={'text':'buy sleep logs for 0.12 XRP'}).status_code==200
    assert market.s.one("SELECT offer FROM postings WHERE buyer='seller'")['offer']==12


def test_record_quantity_is_not_mistaken_for_permission_to_change_the_price(market,monkeypatch):
    from fastapi.testclient import TestClient
    from vaultmarket import app as web
    monkeypatch.setattr(web,'M',market);monkeypatch.setattr(config,'PUBLIC',False)
    assert TestClient(web.app).post('/api/account/seller/chat',json={'text':'sell my sleep logs for 7 nights'}).status_code==200
    assert market.acct('seller')['sell_agent']['min']['sleep_log']==7


def test_old_group_approval_is_archived_without_deleting_its_history(market):
    text='Buyer wants your data. Sell inside a lot of at least 5 people?'
    mid=market.s.insert('chat',account='seller',role='agent',text=text,actions=[{'t':'OK','do':'interest','posting':market.test_post}])
    market.seed()
    old=market.s.one('SELECT * FROM chat WHERE id=?',(mid,))
    assert old['text']==text and old['done']==1
    assert market.s.one("SELECT count(*) n FROM chat WHERE account='seller'")['n']>=2


def test_price_discovery_does_not_mix_xrp_and_test_usd_trade_units(market):
    a=market.s.insert('contracts',asset='XRP',unit_micro=10000,status='settled')
    b=market.s.insert('contracts',asset='test USD',unit_micro=1000000,status='settled')
    market.s.insert('prices',kind='sleep_log',price=8,contract=a)
    market.s.insert('prices',kind='sleep_log',price=900,contract=b)
    assert market.quote('sleep_log')['median']==8


@pytest.mark.parametrize("seller", ["seller", None])
def test_member_negotiation_history_is_private_to_the_participants(market, monkeypatch, seller):
    from fastapi.testclient import TestClient
    from vaultmarket import app as web
    monkeypatch.setattr(web, 'M', market)
    monkeypatch.setattr(config, 'PUBLIC', True)
    for aid in ('u-owner','u-other'):
        market.s.insert('accounts', id=aid, name=aid, type='person')
        market.s.insert('users', username=aid, account=aid)
        market.s.insert('sessions', token=aid, username=aid)
    cid=market.s.insert('contracts',posting=market.test_post,buyer='u-owner',seller=seller,sellers=['seller'],kind='sleep_log',status='rejected',trace={})
    client=TestClient(web.app)
    assert client.get(f'/api/contract/{cid}').status_code==403
    assert cid not in [c['id'] for c in client.get('/api/market').json()['contracts']]
    client.cookies.set(web.COOKIE,'u-other')
    assert client.get(f'/api/contract/{cid}').status_code==403
    client.cookies.set(web.COOKIE,'u-owner')
    assert client.get(f'/api/contract/{cid}').status_code==200
    assert cid in [c['id'] for c in client.get('/api/market').json()['contracts']]
