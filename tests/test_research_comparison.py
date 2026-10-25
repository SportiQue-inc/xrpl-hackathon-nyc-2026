import json
from pathlib import Path


def test_report_uses_the_research_policy_and_receipt_mapping():
    from agentrail import scenario,study
    from tests.llm_doubles import capable_needs
    from scripts.build_research_comparison import report_data
    w=scenario.build_world('mock',':memory:')
    study.ensure(w)
    w.study.payout_currency={pid:'XRP' for pid in w.cohort_people}
    study.set_goal(w,'',capable_needs)
    assert study.approve(w,['owner','compliance'])['ok']
    study.send(w,workers=1)
    d=report_data(w)
    assert len(d['agents'])==50 and d['real_income'] is False
    assert d['paid_minor']==d['engine_paid_minor']>0
    assert len({a['style'] for a in d['agents']})==3
    for a in d['agents']:
        assert abs(a['income'][0]['amount']-sum(r['amount'] for r in a['receipts']))<1e-9
        assert a['consented_items'] and 'purpose' in a['policy_description']
        assert a['income'][0]['amount']<10  # Initial test wallet funds never enter earnings.
    assert any(a['pending']>0 for a in d['agents'])
    assert any(a['sales']==0 for a in d['agents'])


def test_report_routes_publish_only_the_labeled_synthetic_snapshot():
    from fastapi.testclient import TestClient
    from vaultmarket import app
    c=TestClient(app.app)
    assert c.get('/report').status_code==200
    r=c.get('/api/research-report');assert r.status_code==200
    d=r.json();assert d['mode']=='synthetic mock cohort' and not d['real_income']
    assert len(d['agents'])==50 and all(a['id'].startswith('P-') for a in d['agents'])
