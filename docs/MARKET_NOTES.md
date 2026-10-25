# 잠재력 / Market Potential — 근거 자료와 README 섹션

기준일 2026-10-25. 모든 숫자에 출처를 붙였다. **(추정)** 표시는 우리 가정이나 계산이다. 시장조사 회사마다 정의가 달라 범위로 적었다.
순서는 `review/potential-rescore.md` 피치 틀(크기 → 지금 방식 → 빈도의 벽 → 우리가 바꾸는 것 → 흐름 → 수익)을 따른다.

---

## 0. 결론 (한 줄)

데이터는 이미 큰 돈으로 거래되고 있지만 **"큰 계약을 드물게"** 하는 구조다. 연구 하나에 필요한 작은 빈칸(한 사람의 몇 주)은 계약 기간(수개월)과 카드 수수료($0.30 고정) 때문에 아예 거래가 안 된다. 에이전트가 빈칸을 찾고 XRPL이 동의·라이선스·정산을 건당 $0.0001 미만, 3~5초에 끝내면 **작은 거래를 자주** 할 수 있다. 이 흐름은 이미 XRPL에서 1,300만 건을 넘었다.

---

## 1. 크기 (Market size)

| 시장 | 규모 | 성장 | 출처 |
|---|---|---|---|
| AI 학습 데이터셋 | $3.2B (2025) → $16.3B (2033) | CAGR 22.6% | Grand View Research 2026–2033판 ([GII 재판매 페이지](https://www.giikorea.co.kr/report/grvi2018158-ai-training-dataset-market-size-share-trends.html)) |
| AI 학습 데이터셋 (다른 추정) | $2.82B (2024) → $9.58B (2029) | CAGR 27.7% | MarketsandMarkets (보도자료 재게재, [Barchart](https://www.barchart.com/story/news/29285978/ai-training-dataset-market-future-scope-growing-trends-business-growth-size-segmentation-dynamics-and-forecast-to-2029)) |
| 데이터 마켓플레이스 플랫폼 | $1.5B (2024) → $5.7B (2030) | CAGR 25.2% | [Grand View Research](https://grandviewresearch.com/industry-analysis/data-marketplace-market-report) |
| 데이터 마켓플레이스 (넓은 정의) | $3.2B (2025) → $17.1B (2034) | CAGR 19% | [MarketIntelo](https://marketintelo.com/report/data-marketplace-market) |
| 실사용 근거(RWE) 솔루션 | $2.0B~2.6B (2025) → $11.9B (2035) | — | [IMARC](https://www.imarcgroup.com/real-world-evidence-solutions-market), [GMI](https://www.gminsights.com/industry-analysis/real-world-evidence-solutions-market) |
| 데이터 라벨링 대표 기업 | Scale AI 매출 $870M(2024), Meta가 49%를 $14.3B에 인수(2025.6, 기업가치 $29B). Surge AI 매출 약 $1.2B(2024, Sacra 추정) | — | [TechCrunch](https://techcrunch.com/2025/06/13/scale-ai-confirms-significant-investment-from-meta-says-ceo-alexandr-wang-is-leaving/), [TipRanks](https://www.tipranks.com/news/article/meta-platforms-meta-bets-14-3-billion-on-superintelligence-to-secure-ai-crown), [Sacra](https://sacra.com/research/surge-ai) |
| 웨어러블 공급 기반 | 전 세계 출하 6.1억 대(2025, +9.1%). 미국 성인 46%가 웨어러블 보유 | — | [IDC](https://www.idc.com/promo/wearablevendor/vendor), [Rock Health 2025 via Fierce](https://www.fiercehealthcare.com/health-tech/health-wearable-ownership-33-past-decade-rock-health-survey) |

참고: 시장조사 보고서는 정의가 달라 값이 2~5배 벌어진다. 피치에는 보수적인 쪽(Grand View)을 쓴다.

## 2. 지금 방식: 얼마에, 어떻게, 얼마나 걸려

**대형 라이선스 계약 (연 수천만 달러, 몇 년 단위)**

| 사례 | 금액 | 출처 |
|---|---|---|
| Reddit → Google | 연 약 $60M | [Reuters 인용, The Decoder](https://the-decoder.com/reddit-signs-60-million-annual-training-data-deal-with-google/) |
| Reddit 데이터 라이선스 총 계약액(IPO 공시) | $203M | [LLMPulse 정리](https://llmpulse.ai/blog/ai-content-licensing-deals/) |
| News Corp → OpenAI | 5년 $250M 이상(현금+크레딧, 연 약 $50M) | [WSJ 인용, BNN Bloomberg](https://www.bnnbloomberg.ca/openai-inks-deal-with-wall-street-journal-publisher-news-corp-1.2076258) |
| Tempus AI → AstraZeneca·Pathos | 3년 $200M (데이터 라이선스+모델 개발) | [Tempus 1Q25 실적, BusinessWire](https://www.businesswire.com/news/home/20250506572067/en/Tempus-Reports-First-Quarter-2025-Results) |
| 23andMe → Regeneron (파산 경매) | $256M, 약 1,500만 명 → 1인당 약 $17 | [pharmaphorum](https://pharmaphorum.com/news/regeneron-swoops-genetic-testing-firm-23andme), [Motley Fool](https://www.fool.com/investing/2025/05/24/does-the-23andme-acquisition-make-regeneron-a-buy/) |

**소매·중개 단가 (싸지만 질이 낮고 동의가 불분명)**

| 항목 | 단가 | 출처 |
|---|---|---|
| 데이터 브로커의 정신건강 관련 레코드 | 레코드당 $0.12~0.32, 구독 연 $75k~100k | [Duke 연구 보도, SiliconANGLE](https://siliconangle.com/2023/02/13/study-finds-data-brokers-selling-americans-mental-health-data/) |
| 선호도 비교 라벨(RLHF) | 비교 1건 $0.10~0.50 | [NextWealth (판매사 자료, 참고용)](https://www.nextwealth.com/?p=14642) |
| 의료·법률 전문가 라벨 | 작업 1건 $1.50~8.00+ | 같은 출처 |
| UK Biobank 연구 접근료 | 3년 £3,000 / £6,000 / £9,000 (등급별) | [UK Biobank](https://www.ukbiobank.ac.uk/use-our-data/fees/) |
| All of Us 참여자 보상 | 1회 $25 | [All of Us](https://joinallofus.org/what-participants-receive) |

**걸리는 시간**

| 항목 | 기간 | 출처 |
|---|---|---|
| 임상 데이터 요청 → 접근 (Yale YODA) | 중앙값 80일, 그중 데이터 사용 계약(DUA) 체결만 35일 | [YODA Dashboard 2026.7](https://yoda.yale.edu/wp-content/uploads/2026/07/YODA-Project-Dashboard-Metrics-July-2026.pdf) |
| EHR 기반 실용 임상 | DUA 문제로 6개월 이상 지연 다수 | [Duke/NIH Collaboratory](https://dcricollab.dcri.duke.edu/sites/NIHKR/KR/04_Marsolo_DUAs_Administrative.pdf) |
| 데이터 파트너 온보딩 | 수주~수개월 | [MedMorph IG](https://carradora.atlassian.net/wiki/spaces/MedMorph/pages/858980359/Research+Use+Case) |

## 3. 빈도의 벽: 큰 계약만 성사되고 작은 빈칸은 안 산다

- **거래 빈도:** 공개된 AI 콘텐츠 라이선스 계약은 2023년 12건, 2024년 28건, 2023~2026.6 누적 91건뿐이다 ([Media and the Machine](https://mediaandthemachine.substack.com/p/ai-content-licensing-deals-june-2026)). 한 건이 연 수천만 달러다. 시장은 "연 수십 건의 큰 계약"으로 움직인다.
- **빈칸의 비용:** 임상 참여자 1명 모집에 $2,273(Tufts) ~ $6,533. 중도 이탈 후 대체는 약 3배. 이탈률은 후기 임상 19.1%(Tufts 2019), 일반적으로 15~40%. 비순응 20~30%면 같은 검정력에 표본 50% 증원이 필요 ([Tufts via Drug Development & Delivery](https://drug-dev.com/drug-developers-are-making-strides-in-streamlining-patient-recruitment-retention-for-clinical-trials/), [Clinical Leader](https://www.clinicalleader.com/doc/understanding-clinical-trial-patient-attrition-0001), [Outsourced Pharma](https://www.outsourcedpharma.com/doc/considerations-for-improving-patient-0001)).
- **원격·웨어러블 연구는 더 심하다:** 8개 원격 디지털 헬스 연구, 10만 명 분석에서 참여 유지 기간 중앙값 **5.5일** ([Pratap et al., npj Digit Med 2020](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7026051/)). Fitbit 기반 2년 우울증 연구도 43주 유지율 67.6%, 이탈은 무작위가 아니어서 편향을 만든다 ([Zhang et al., npj Digit Med 2023](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9938183/)). 같은 연구에서 **보상은 유지 기간을 약 22일 늘렸다**(Pratap).
- **결론:** 연구 하나가 필요한 건 "특정 사람들의 특정 몇 주"다. 이 빈칸은 금액이 작아 80일짜리 계약을 맺을 가치가 없고, 카드로 쪼개 보상하면 수수료가 보상보다 커진다. 그래서 지금은 아예 거래되지 않고, 연구는 표본을 더 뽑는 비싼 길을 간다.

## 4. 우리가 바꾸는 것: 거래 비용을 0에 가깝게

| | 카드 (Stripe 미국 표준) | XRPL |
|---|---|---|
| 건당 수수료 | 2.9% + $0.30 ([Stripe](https://stripe.com/nl/help/pricing)) | 기본 10 drops = 0.00001 XRP ([xrpl.org](https://xrpl.org/transaction-cost.html)), 약 $0.00002 (XRP $2 가정) |
| $20 주간 기여 정산 | $0.88 (4.4%) **(계산)** | ≈ $0.00002 |
| $2.86 일 단위 정산 | $0.38 (13.4%) **(계산)** | ≈ $0.00002 |
| $0.05 요청당 결제 (x402) | 불가능 ($0.30 > 금액) | 가능 |
| 확정 시간 | 영업일 단위 정산, 차지백 최대 수개월 | 3~5초, 되돌릴 수 없는 확정 |
| 조건부 지급 | 별도 계약·에스크로 서비스 | Escrow(조건 충족 시 해제), MPT 라이선스, Credential 내장 |

에이전트가 빈칸 추론 → 참여자 개인 에이전트가 회차별 동의 → Escrow·MPT·Credential로 한 번에 정산. 80일짜리 계약이 **분 단위 회차**로 바뀐다.

## 5. 흐름: 에이전트 결제는 이미 커지고 있다

| 지표 | 값 | 출처 |
|---|---|---|
| XRPL 에이전트 거래 누적 | 13,489,468건, x402 판매자 168곳 (2026.10), 첫 100만 건은 2026.7.8 → **약 3개월 만에 13배** | RippleX J. Ayo Akinyele, XRPL AI Hub ([Yellow](https://yellow.com/news/ai-agents-13m-payments-xrp-ledger), [KuCoin](https://www.kucoin.com/news/flash/xrp-ledger-agentic-payments-surpass-13-million-transactions), [crypto.news](https://crypto.news/ex-ripple-exec-on-xrps-13m-ai-payments-whats-next/)) |
| XRPL 정산액 | 약 6,982 XRP + 12,010 RLUSD (건당 금액이 매우 작다는 뜻) | 같은 출처 |
| x402 on Base | 누적 1.38억 건(2026 3Q), 87%가 $0.0001~0.10 사이 | [Chainalysis via Cointelegraph](https://cointelegraph.com/news/agentic-payment-activity-surpasses-100m-transactions-on-base), [AI Weekly](https://aiweekly.co/alerts/chainalysis-base-x402-agentic-payments-hit-138m-in-q3-with-87-under-10-cents) |
| x402 재단 | 2026.7 Linux Foundation 산하 출범, Google·Mastercard·Stripe·Visa 참여 | 2차 보도 ([KuCoin](https://www.kucoin.com/news/flash/coinbase-processes-1t-in-stablecoin-payments-annually-x402-hits-160m-transactions)), 제출 전 원문 확인 필요 |
| 에이전트 커머스 2030 전망 | 미국 e커머스의 10~20%, $190B~385B (Morgan Stanley) / 세계 $3~5T 중개 (McKinsey) | [Nevermined 정리](https://nevermined.ai/blog/agentic-commerce-growth-statistics), [Stellagent](https://stellagent.ai/insights/agentic-commerce-market-size-forecast-2030) (2차 출처) |

주의: 거래 수는 실제 매출과 다르다. 자동 반복 요청이나 실험 앱이 섞여 있을 수 있다 (출처들도 같은 주의를 단다).

## 6. 수익: 아래에서 쌓는 계산 (전부 추정)

**가정 (추정)**
- 기여 단위 = 한 참여자의 1주 종합 기록(웨어러블+병원+설문). 기관 지불 **$20/참여자-주**. 모집비 $2,273~6,533 대비 1/100 수준이라 기관은 빈칸을 사는 게 표본 증원보다 싸다.
- 수수료(take rate) **10%**, 나머지 90%는 참여자 보상·데이터 보관 기관 몫.
- 기관 구독 **$12,000/연구/년** (빈칸 추론 에이전트, 동의 감사 로그, MCP 접근).
- 정산은 주 1회 이상 → 참여자-주 1건 = XRPL 정산 1건 이상.

| | 연구 수 | 연구당 참여자 | 연간 참여자-주 | 정산 건수/년 | 기여 총액 | 수수료 10% | 구독 | 연 매출 |
|---|---|---|---|---|---|---|---|---|
| 1년차 (파일럿) | 10 | 200 | 12 | 24,000 | $0.48M | $48k | $120k | **$0.17M** |
| 2년차 | 60 | 400 | 20 | 480,000 | $9.6M | $0.96M | $0.72M | **$1.7M** |
| 3년차 | 300 | 500 | 26 | 3.9M | $78M | $7.8M | $3.6M | **$11.4M** |

- 3년차 300개 연구는 해마다 새로 시작되는 임상만 약 3.5만 건(2022년 35,338건, [J Clin Med 2024](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11989625/))인 것과 비교해 1% 미만이다.
- 연 390만 건 정산을 카드로 하면 수수료만 약 $3.4M(건당 $0.88)이고, XRPL은 약 $80 **(계산)**. 이 차이가 이 구조가 XRPL에서만 성립하는 이유다.

**TAM / SAM / SOM (추정)**

| | 정의 | 규모 | 근거 |
|---|---|---|---|
| TAM | AI 학습 데이터 + RWE 솔루션 + 데이터 마켓플레이스 플랫폼 (2025) | 약 $7B, 2033년 전후 $30B+ | 1절 표 합산(각 보고서 예측 연도 다름) ($3.2B + $2.0~2.6B + $1.5B), 일부 중복 |
| SAM | 사람 단위 종단 건강 데이터로 연구·AI를 하는 기관 (RWE + AI 학습 데이터 중 헬스케어) | 약 $2.5B | RWE $2.0~2.6B 기준 (추정) |
| SOM | 3년차 위 계산 | $11.4M 매출 / $78M 기여 총액 | SAM의 약 0.5% |

**확장 (같은 엔진, 동의 층만 가볍게):** 기업 간 AI 학습 데이터에서 2030년 시장($8.6B, Grand View 2025–2030판)의 5%만 이 레일로 오고 수수료 3%면 연 약 $13M 추가 **(추정)**.

---

## README 섹션 (붙여 넣기용)

### 🇰🇷 잠재력과 시장

**데이터는 비싸게 팔리지만, 드물게 팔린다.** AI 학습 데이터 시장은 2025년 $3.2B에서 2033년 $16.3B로 커지고(연 22.6%), 실사용 근거(RWE) 시장도 $2~2.6B 규모다. 그런데 거래는 Reddit→Google 연 $60M, News Corp→OpenAI 5년 $250M, Tempus→AstraZeneca 3년 $200M 같은 큰 계약으로만 일어난다. 공개된 AI 데이터 라이선스는 2024년 한 해 28건이다. 연구 데이터 하나를 받는 데 중앙값 80일이 걸리고(Yale YODA), 그중 35일이 계약 체결이다.

**연구에 필요한 건 작은 빈칸이다.** 임상 참여자 한 명 모집에 $2,273~6,533이 들고, 15~40%가 중간에 빠진다. 원격 웨어러블 연구는 참여 유지 기간 중앙값이 5.5일이다. 빠진 몇 주를 채우는 일은 금액이 작아 80일짜리 계약을 맺을 수 없고, 카드로 보상하면 $0.30 고정 수수료가 보상보다 크다. 그래서 지금은 거래 자체가 없고, 연구는 표본을 더 뽑는 비싼 길을 간다.

**우리는 거래 비용을 0에 가깝게 만든다.** 연구 기관의 에이전트가 빠진 데이터를 추론하고, 참여자의 개인 에이전트가 회차별로 동의해 기여하고, XRPL이 Escrow·MPT 라이선스·Credential로 3~5초 안에 건당 $0.0001 미만으로 정산한다. $20짜리 주간 기여를 카드로 정산하면 $0.88, XRPL로는 $0.00002다. 에이전트 결제는 이미 XRPL에서 1,350만 건(x402 판매자 168곳)을 넘었고, 첫 100만 건 이후 3개월 만에 13배가 됐다.

**수익 (추정):** 참여자-주당 $20, 수수료 10%, 연구당 구독 $12k. 3년차 300개 연구 × 500명 × 26주 = 연 390만 건 정산, 기여 총액 $78M, 매출 $11.4M. 매년 새로 시작되는 임상 약 3.5만 건의 1% 미만이다. 가장 까다로운 사람 단위 건강 기록에서 동의·철회를 푼 같은 엔진은, 동의 층만 가볍게 하면 기업 간 AI 데이터·로봇 센서 데이터로 그대로 확장된다.

### 🇺🇸 Potential & Market

**Data sells for a lot, but rarely.** The AI training dataset market grows from $3.2B (2025) to $16.3B (2033, 22.6% CAGR), and real-world evidence solutions are a $2–2.6B market. Yet supply moves through a few large contracts: Reddit→Google (~$60M/yr), News Corp→OpenAI ($250M+ over 5 years), Tempus→AstraZeneca ($200M over 3 years). Only 28 AI content-licensing deals were publicly reported in 2024. Getting research data takes a median of 80 days (Yale YODA), 35 of them just to sign the data use agreement.

**Research needs small gaps filled.** Recruiting one trial participant costs $2,273–6,533, and 15–40% drop out. In remote wearable studies, median retention is 5.5 days. Filling a few missing weeks is too small for an 80-day contract, and paying for it by card costs more than the payment itself ($0.30 fixed fee). So today that trade doesn't happen at all, and studies over-recruit instead.

**We drive the transaction cost toward zero.** The institution's agent infers what is missing, each participant's personal agent consents per episode, and XRPL settles with Escrow, MPT licenses and Credentials in 3–5 seconds for under $0.0001. A $20 weekly contribution costs $0.88 to settle by card and about $0.00002 on XRPL. Agentic payments on XRPL already passed 13.5M transactions across 168 x402 merchants, 13× in three months after the first million.

**Revenue (estimate):** $20 per participant-week, 10% take rate, $12k/study/year subscription. Year 3: 300 studies × 500 participants × 26 weeks = 3.9M settlements/year, $78M contributed value, $11.4M revenue, under 1% of the ~35k clinical trials started each year. The engine that handles consent and revocation for person-level health records, the hardest case, extends to B2B AI training data and robotics sensor data by lightening the consent layer.

| Layer | Size | Source |
|---|---|---|
| TAM: AI training data + RWE + data marketplaces (2025) | ~$7B | Grand View, IMARC, GMI (sum, overlapping, estimate) |
| SAM: institutions using person-level longitudinal health data | ~$2.5B | RWE market (estimate) |
| SOM: Year 3 bottom-up | $11.4M revenue / $78M GMV | Our model (estimate) |

---

## 피치 한 장 (40초 영상용 문장)

1. "AI 데이터 시장은 $3.2B, 매년 22%씩 큰다."
2. "그런데 Reddit, News Corp 같은 연 수천만 달러짜리 계약만, 1년에 수십 건 성사된다. 연구 데이터 하나 받는 데 80일."
3. "연구에 필요한 건 빠진 몇 주다. 참여자 한 명 다시 모으는 데 $2,000 넘게 들고, 웨어러블 연구는 5.5일이면 절반이 떠난다. 그 빈칸은 너무 작아서 아무도 안 판다."
4. "에이전트가 빈칸을 찾고, 참여자의 에이전트가 동의하고, XRPL이 3초에 $0.00002로 정산한다. 카드로는 $0.88."
5. "XRPL 에이전트 결제는 3개월 만에 100만 건에서 1,350만 건이 됐다."
6. "3년차 300개 연구, 연 390만 건 정산, 매출 $11M. 같은 엔진이 로봇 데이터에서 이미 Testnet으로 돈다."

## 남은 확인 사항

- Yellow·Grand View 원문 페이지는 이 환경에서 직접 열리지 않아 검색 요약으로 확인했다. 제출 전 링크를 한 번 눌러 숫자를 확인하면 좋다.
- XRP 가격은 제출 시점 시세로 $0.00002를 다시 계산한다.
- 에이전트 커머스 2030 전망(McKinsey, Morgan Stanley)은 2차 출처라 README 본문에는 넣지 않았다.
