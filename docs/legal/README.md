# Legal requirements built into the design

> Not legal advice. The demo uses synthetic data and XRPL Testnet only. A live service needs review by
> regulators and counsel in each country. These are legal requirements reflected in the design, not a
> claim of compliance.

## Legal requirements -> product rules

| What the law requires | The product rule we built | Basis |
|---|---|---|
| Separate consent for health data, kept apart from other consents | Separate consents for sensitive data, third-party provision and international transfer, each hashed and tied to the signature | Korea PIPA Arts. 22, 23; 45 CFR 46.116 |
| No use beyond the consented scope | Code checks recipient, purpose, items and period on every round and again before the key is published; the LLM cannot widen it | PIPA Art. 17 |
| Researchers must not identify the person; no other studies | Per-study participant number and minimum items only; the link stays with the person's agent; risky item combinations refused; consent states that data, even with identifiers removed, will not be used for other studies | PIPA Arts. 28-2 to 28-5; 45 CFR 46.116(b)(9); HIPAA 164.514 (reference) |
| Withdraw at any time, without penalty | Three withdrawal options; key release stops at once; the institution is asked to destroy person-level copies and its confirmation is recorded (same rule in every country; only aggregate statistics remain); withdrawal history is never an input to pay or priority (tested) | PIPA Art. 37; Bioethics Act Art. 16; 45 CFR 46.116(b)(8) |
| Access from abroad is an international transfer | Countries, recipients, purpose, items and retention disclosed; separate consent; records stay in the person's country | PIPA Art. 28-8 |
| The IRB decides approval | Agents never create approval; an XRPL Credential only shows the issuer's attestation | Bioethics Act Art. 15; 45 CFR 46.112 |
| Compensation accrues with participation, without undue inducement | One escrow rail, three schedules by study type: prospective (50% of a verified week at key reveal, +10 points per consecutive week up to 90%, weekly rate ×1.1/×1.2/×1.3 after 2/4/8 weeks; the rest after a short review, paid by default), retrospective (paid whole on delivery after the certificate, sample and provenance checks), hybrid (baseline once, then prospective weeks); paid money is never taken back on chain | Bioethics Act Art. 16(1)5; FDA 2018 payment guidance |
| Holding or moving others' funds needs a licence | Non-custodial: the platform only drafts transactions; the institution's wallet signs and pays; the platform never receives or sends funds | Korea AML Act (VASP); FinCEN FIN-2019-G001 |
| No personal data on a public ledger | Only payment and licence state and hashes on chain; no health values, study names or conditions | PIPC blockchain guideline (2026) |

FDA guidance (2018) on payment to research subjects: "Any credit for payment should accrue as the
study progresses and not be contingent upon the subject completing the entire study." This is the
basis for per-round escrows and a small, separate completion bonus.

## 법적 요구사항 -> 제품 규칙

> 법률 자문이 아닙니다. 데모는 합성 데이터와 XRPL Testnet만 사용합니다. 실서비스 전 당국·전문가 확인이 필요합니다.

| 법이 요구하는 것 | 우리가 만든 장치 | 근거 |
|---|---|---|
| 건강정보는 따로 동의, 동의 사항은 구분해서 | 민감정보·제3자 제공·국외 이전 동의를 각각 따로 받고 서명과 연결 | 개인정보 보호법 제22·23조, 45 CFR 46.116 |
| 동의 범위 밖으로 제공하면 안 됨 | 받는 자·목적·항목·기간을 코드가 매 회차, 키 공개 직전에 다시 검사. LLM은 범위를 넓히지 못함 | 개인정보 보호법 제17조 |
| 연구자는 개인을 알아보면 안 됨 | 연구별 참여번호와 최소 항목만 전달. 사람과 번호를 잇는 정보는 본인 에이전트에 따로 보관하고, 위험한 항목 조합은 차단 | 개인정보 보호법 제28조의2~5, HIPAA 164.514 참고 |
| 언제든 불이익 없이 철회 | 철회 3종. 즉시 키 공개 차단, 기관 사본 파기 요청과 회신 기록. 철회 이력은 대가·우선순위 판정에 쓰지 않음(테스트로 고정) | 개인정보 보호법 제37조, 생명윤리법 제16조, 45 CFR 46.116(b)(8) |
| 해외에서 조회해도 국외 이전 | 나라·받는 자·목적·항목·기간을 알리고 따로 동의. 개인 기록은 본인 나라에 보관 | 개인정보 보호법 제28조의8 |
| IRB 승인은 IRB가 판단 | 에이전트는 승인을 만들지 않음. XRPL Credential은 발급 기관의 진술을 표시할 뿐 | 생명윤리법 제15조, 45 CFR 46.112 |
| 대가는 참여에 따라, 부당한 유인 없이 | Escrow 하나에 연구 유형별 지급 방식 세 가지. 전향적: 검증된 주의 50%를 키 공개 때 지급하고 연속 주마다 10%p씩 올려 최대 90%, 2/4/8주 연속이면 주당 단가 ×1.1/×1.2/×1.3, 나머지는 짧은 검수 뒤 기본 지급. 후향적: 인증서·샘플·출처 확인 뒤 전달 시 전액. 하이브리드: 기준 데이터 1회 + 전향적 추적 주. 지급된 돈은 원장에서 되찾지 않음 | 생명윤리법 제16조 제1항 제5호, FDA 2018 지급 지침 |
| 남의 돈을 맡으면 인허가 | 기관이 직접 서명해 지급하고 플랫폼은 키와 자금을 갖지 않음 | 특정금융정보법, FinCEN FIN-2019-G001 |
| 공개 원장에 개인정보 금지 | 원장에는 지급·라이선스 상태와 해시만. 건강정보·연구명·질환명은 기록하지 않음 | 개인정보보호위원회 블록체인 가이드라인(2026) |

## Payment and penalty rules (engine)

Implemented in `agentrail/payout.py`, tested in `tests/test_payout.py`:

1. Decline, pause and withdrawal events are never inputs to payout or sanction decisions.
2. Penalties apply only to fraud (fabricated data, someone else's device or data, several accounts)
   and to repeatedly missing an accepted round. Code detects signals; a named reviewer confirms
   after notice and a response period. The LLM never judges.
3. Pay follows the study type (`agentrail/payout_schedule.py`). Prospective: 50% of a verified week
   at key reveal, +10 points for each consecutive verified week up to 90%, and the weekly rate steps up
   ×1.1/×1.2/×1.3 after 2/4/8 consecutive weeks; a gap resets the curve and never takes back what was
   paid. The rest is held in an escrow with FinishAfter (7 days, up to 14 more if fraud is suspected).
   Review passed or time out -> paid. Unpaid only on confirmed fraud. Retrospective: paid whole on
   delivery, after the certificate, hashed sample and provenance checks. Hybrid: a retrospective
   baseline once, then prospective follow-up weeks. A tampered contribution fails the provenance check
   before payment and gets 0.
4. After withdrawal, held parts are still paid; data destroyed before review counts as passed.
5. A completion bonus is a separate escrow and returns to the institution on withdrawal.
6. Money already paid is never taken back on chain; confirmed fraud records a repayment claim
   only. Trust levels stay off the ledger.
7. Two missed accepted rounds in a row pause automatic requests (one tap resumes); priority and pay
   rules do not change.

## More in this folder

- [verified-articles-kr.md](verified-articles-kr.md): Korean articles checked against the preserved original texts
- [verified-articles-us.md](verified-articles-us.md): US rules checked against the original texts
- [background.md](background.md): summary of a prior regulatory consultation, public precedents for each mechanism, and where they show in the design
- [payment-and-penalty-policy.md](payment-and-penalty-policy.md): penalty scope, holdback and consent wording (Korean; [미검증] marks kept)
