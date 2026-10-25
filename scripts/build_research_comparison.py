"""Reproduce a synthetic research-cohort report with the existing policy and receipt mapping."""
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone


def report_data(w):
    from agentrail import study, uniqdata_port
    from agentrail.scenario import XRP
    view=study.study_view(w)
    start=datetime(2026,9,7,tzinfo=timezone.utc).timestamp()
    agents=[]
    for pid,pa in w.cohort_people.items():
        pseudonym=pa.vault.pseudonym(study.LAB)
        policy=dict(w.store.one('SELECT * FROM consents WHERE person_id=? AND buyer_id=?',pid,study.LAB))
        cs=[c for c in view['contributions'] if c['pseudonym']==pseudonym]
        hbs=[h for h in view['payout']['holdbacks'] if h['person']==pid]
        receipts=uniqdata_port.payout_receipts(cs,'mock',hbs)
        paid=sum(r['amount_minor'] for r in receipts)
        # Review holdbacks are earned but not released; conditional completion bonuses are separate.
        pending=sum(round(h['amount_xrp']*XRP) for h in hbs if h['kind']=='round' and h['status'] in ('held','suspected'))
        req=next((r for r in view['responses']['people'] if r['person']==pid),{})
        timeline=[{'asset':'Simulated XRP','amount':r['amount_minor']/XRP,'at':start+(max(r['metadata'].get('weeks') or [8])-.5)*7*86400} for r in receipts]
        mode=policy['automation']
        agents.append({'id':pid,'name':pseudonym,'style':{'auto_all':'Within approved scope','auto_standard':'Standard data automatic','confirm_each':'Confirm each round'}[mode],
          'approval':'ask' if mode=='confirm_each' else 'auto','blocked_purposes':[], 'minimums':{'Minimum per data item':policy['min_price_drops']/XRP},'floor_ratio':0,
          'policy_description':f"{mode}; consented weeks {policy['period_from']}–{policy['period_to']}; purpose {policy['purpose']}",
          'sales':len(receipts),'income':[{'asset':'Simulated XRP','amount':paid/XRP}], 'pending':pending/XRP,'response_status':req.get('status','not requested'),
          'consented_items':json.loads(policy['items']),'receipts':timeline,'receipt_refs':[r['payout_intent_ref'] for r in receipts]})
    return {'start':start,'end':start+8*7*86400,'minutes':0,'agents':agents,'assets':['Simulated XRP'],'default_asset':'Simulated XRP','unit':1,
       'generated_at':datetime.now(timezone.utc).isoformat(),'mode':'synthetic mock cohort','real_income':False,
       'engine_paid_minor':sum(round(c['amount_xrp']*XRP) for c in view['contributions'] if c['status']=='delivered'),
       'paid_minor':sum(round(r['amount']*XRP) for a in agents for r in a['receipts']),
       'study_budget':view['study']['budget_xrp'],'period_weeks':8,
       'source_modules':['agentrail.study','agentrail.policy.PersonalConsentPolicy','agentrail.uniqdata_port.payout_receipts'],
       'note':'Fixed synthetic 50-person, 8-week research test using the existing consent policy engine and UniQdata payout-receipt mapping. Mock receipts are not real income or live UniQdata records. All test participants keep XRP for a common comparison unit; initial wallet funding is excluded. Participants have different missing-data opportunities and consent scopes, so this is not a causal estimate of agent settings.'}


if __name__=='__main__':
    import os
    os.environ['LLM_PROVIDER']='none'
    from agentrail import scenario,study
    from tests.llm_doubles import capable_needs
    w=scenario.build_world('mock',':memory:')
    study.ensure(w)
    w.study.payout_currency={pid:'XRP' for pid in w.cohort_people}
    study.set_goal(w,'',capable_needs)
    assert study.approve(w,['owner','compliance'])['ok']
    study.send(w,workers=1)
    result=report_data(w)
    assert len(result['agents'])==50 and result['paid_minor']==result['engine_paid_minor']
    result['engine_revision']=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    target=Path('prototypes/data-vault-market/server/vaultmarket/static/research-report.json')
    target.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps({'participants':50,'paid_mock_xrp':result['paid_minor']/1000000,'real_income':False,'path':str(target)}))
