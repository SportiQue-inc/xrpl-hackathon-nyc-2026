# Health data catalog and tiered consent

법률 자문 아님 · 합성 데이터 · Testnet. Legal requirements are reflected in the design; this is not a compliance claim.

## The catalog (`agentrail/catalog/columns.py`)

46 columns, each with a sensitivity tier, the GA4GH DUO codes a request must carry, a retention period and a deletion rule. All values are synthetic, including the genomic variants (a few per gene at BRCA1/2, CYP2C19, CYP2D6, APOE, SLCO1B1) and the images (DICOM-like metadata plus a 16×16 pixel grid).

| tier | meaning | columns | DUO required | retention | re-identification risk class |
|---|---|---|---|---|---|
| T0 | everyday | steps, sleep, sleep efficiency, resting HR, HRV, active minutes, active energy, weight, body fat, SpO2, respiratory rate, skin temperature, screen time | HMB | 365 d | low |
| T1 | lifestyle | meal energy, protein, carbs, sugar, caffeine, alcohol, water, medication-taking log, mood, stress, fatigue, PSQI, smoking | HMB | 365 d | moderate |
| T2 | clinical | diagnoses, prescriptions, HbA1c, LDL, creatinine, glucose, TSH, blood pressure, clinic HR, BMI, allergies, procedures | HMB, IRB | 180 d | high |
| T3 | highly sensitive | genomic variants, pharmacogenomic variants, CT, MRI, mental health diagnoses, PHQ-9, cycle log, pregnancy history | HMB, IRB, TS, NPOA (+ GSO for genomic) | 90 d | identifying by itself |

T0 and T1 live in the person's own store (UniQdata write API). T2 and T3 have no concept there and are an engine-side source. `GET /api/catalog` returns every column card.

## Tiered consent (`agentrail/catalog/scope.py`)

1. **Restrictions that travel with the data come first.** A request must carry every DUO code its columns require. T2 and up need a verified ethics (IRB) credential. Genomic columns need GSO. These checks can only narrow what happens next; no setting widens them.
2. **Pre-consented scope runs at once.** A standing grant is a level the owner already agreed to: up to a tier, for named purposes, for classes of institution (academic, hospital, commercial), at home or also abroad. A request at or below it is approved by the agent and logged.
3. **Everything else goes to a safety gate.** That covers every T3 request, every time, and any new scope: a higher tier, a new purpose, a new class of institution, or a transfer abroad. Pending requests are bundled per institution into one consent package. The package shows:
   - the institution, the studies and why
   - the re-identification risk class per tier, and whether the data goes abroad
   - for genomic data, a warning about blood relatives and about permanence
   - what that institution already receives, and whether this is a first or an additional request
   - the retention period per column

   The owner approves with one fresh Touch ID assertion bound to the package hash (stale, foreign-device or other-package assertions are refused). Approving can widen the standing grant for the non-T3 part, so next week runs on its own. T3 never becomes standing.
4. **Every decision is logged and revocable.** Revoking an automatic approval also revokes the grant behind it, so the next request goes back to the gate. A declined study is not asked again.

## The bottleneck, in numbers (`agentrail/catalog/simulate.py`)

50 synthetic owners, 6 studies (sleep, cardiology with labs, a nutrition study abroad, pharmacogenomics, imaging, a commercial wellness product), 1 to 12 weekly requests each. Owner response time is exponential with an 18-hour mean, which is an assumption, not a measurement.

| | manual (tick every column, every study, every week) | agent with tiered consent |
|---|---|---|
| owner actions | 11,600 column approvals in 2,300 sittings | 233 Touch ID approvals (50× fewer) |
| approved by the agent at once | none | 1,792 requests |
| median hours from request to paid | 12.0 | under a minute |
| paid within 48 hours | 92.7% | 99.4% |

For the researcher, a median of 42 of the 50 owners deliver each study-week within 48 hours, so there are offers to choose among. Quality before the trade is the next piece (the pre-trade quality certificate).
