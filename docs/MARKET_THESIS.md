# 왜 지금, 왜 중요한가: 데이터 시장 전체에서 AgentRail의 자리

기준일 2026-10-25. 숫자마다 출처를 붙였다. 시장조사 회사마다 정의가 달라서 범위로 적었다. **(추정)**은 우리 계산이다. 세부 단가와 수익 모델은 [research/market-potential.md](../research/market-potential.md)에 있다.

## 0. 한 문단 결론 (테제)

지금까지 데이터 경제는 **사람에 관한 데이터를 그 사람 없이 거래하는 구조**였다. 데이터 브로커 시장만 연 $300~435B이다. 건강 데이터는 병원, 기기 회사, 중개사 사이를 오가며 IQVIA 같은 중개사가 연 $16B 매출을 낸다. 그런데 데이터를 만든 사람에게 돌아가는 몫은 거의 없다(23andMe 파산 경매에서 1인당 약 $17).

지금 이 구조를 동시에 뒤집는 힘이 세 개 있다.
1. **AI의 데이터 벽**: 공개 텍스트는 2026~2032년에 바닥난다. 다음 가치는 동의받은 비공개 종단 데이터로 이동한다.
2. **데이터 주권의 법제화**: EU 건강데이터공간(EHDS), 미국 TEFCA 개인 접근, 한국 건강정보 고속도로가 사람이 자기 기록을 직접 꺼낼 권리를 만들고 있다. 동시에 FTC는 동의 없는 민감 데이터 거래를 막고 있다.
3. **에이전트가 지갑을 가졌다**: x402 거래는 1억 건을 넘었고, 87%가 10센트 미만이다.

세 흐름이 만나는 곳에 다음 데이터 시장이 있다. **사람이 자기 에이전트로 참여하고, 회차마다 동의하고, 직접 보상받는 시장**이다. 그중 가장 비싸고 가장 어려운 영역이 한 사람의 종단 건강 기록이다. AgentRail은 이 시장의 동의·라이선스·정산 레일이다. 가장 어려운 경계를 먼저 풀었기 때문에 AI 학습 데이터와 기업 간 데이터로 그대로 넓어진다.

## 1. 데이터 시장 전체 지도

| 층 | 규모 | 누가 돈을 버나 | 출처 |
|---|---|---|---|
| 데이터 브로커 (전체) | 2025년 $298B~434B | 동의가 불분명한 수집·재판매 사업자 | [SNS Insider](https://www.snsinsider.com/press-release/global-data-brokers-market), [TBRC via GII](https://www.gii.tw/report/tbrc1730822-data-broker-global-market-report.html), [ResearchAndMarkets via GlobeNewswire](https://www.globenewswire.com/news-release/2025/02/14/3026669/0/en/global-data-broker-market) |
| 정밀의료 | 2025년 $82B~118B | 제약, 진단 기업 | [IMARC](https://www.imarcgroup.com/precision-medicine-market), [Fortune BI](https://www.fortunebusinessinsights.com/markt-f-r-pr-zisionsmedizin-110463) |
| 임상시험 | 2025년 $55B~87B | CRO, 제약 | [GMI](https://www.gminsights.com/toc/details/clinical-trials-market), [SNS Insider](https://www.snsinsider.com/press-release/global-clinical-trials-market) |
| 헬스케어 AI | $21.7B(2025) → $110.6B(2030), 연 38.6% | AI·의료 기업 | [MarketsandMarkets](https://www.marketsandmarkets.com/PressReleases/artificial-intelligence-healthcare.asp) |
| AI 학습 데이터셋 | $3.2B(2025) → $16.3B(2033), 연 22.6% | 데이터 공급·라벨링 기업 | Grand View (재판매 페이지, 원문 미확인) |
| 실사용 근거(RWE) 솔루션 | $2.0B~2.6B(2025) | RWD 중개사 | [IMARC](https://www.imarcgroup.com/real-world-evidence-solutions-market), [GMI](https://www.gminsights.com/industry-analysis/real-world-evidence-solutions-market) |
| 데이터 마켓플레이스 플랫폼 | $1.5B(2024) → $5.7B(2030) | 플랫폼 | [Grand View](https://grandviewresearch.com/industry-analysis/data-marketplace-market-report) |
| 대표 중개사 | IQVIA 2025 매출 $16.3B. Datavant 기업가치 약 $7B(비상장 추정). Scale AI 기업가치 $29B(Meta 49% $14.3B) | 중개사 | [IQVIA](https://www.iqvia.com/newsroom/2026/02/iqvia-reports-fourth-quarter-and-full-year-2025-results-issues-full-year-2026-guidance), [Premier Alts](https://www.premieralts.com/companies/datavant/valuation), [TechCrunch](https://techcrunch.com/2025/06/13/scale-ai-confirms-significant-investment-from-meta-says-ceo-alexandr-wang-is-leaving/) |
| **데이터를 만든 사람** | 23andMe 1,500만 명이 $256M에 경매됨 → 1인당 약 $17. All of Us 참여 보상 1회 $25 | 거의 없음 | [pharmaphorum](https://pharmaphorum.com/news/regeneron-swoops-genetic-testing-firm-23andme), [All of Us](https://joinallofus.org/what-participants-receive) |

**읽는 법:** 돈은 수천억 달러 단위로 도는데, 그 데이터의 원천인 사람은 거래에 없다. 거래 형태도 두 가지뿐이다. 동의가 불분명한 대량 재판매(브로커), 아니면 몇 년짜리 대형 계약(Reddit→Google 연 $60M, Tempus→AstraZeneca 3년 $200M)이다. **"특정 사람의 특정 몇 주"를 동의받아 거래하는 형태는 아예 없다.**

## 2. 왜 지금인가: 세 가지 구조 변화

| 변화 | 근거 | 무엇이 닫히고 무엇이 열리나 |
|---|---|---|
| **1. AI의 데이터 벽** | 품질 기준을 넘는 공개 텍스트 약 300조 토큰을 2026~2032년 사이에 다 쓴다(Epoch AI, 2024 추정). 그래서 AI 기업이 대형 라이선스를 사기 시작했다(공개 계약 2023년 12건 → 2024년 28건) | 닫힘: 웹 크롤링으로 공짜 데이터. 열림: **동의받은 비공개·전문·종단 데이터**의 가치. 건강 AI는 특히 한 사람의 시간축 기록이 필요하다 |
| **2. 데이터 주권 법제화** | EU EHDS 2025.3 발효, 데이터 접근 기관 지정 2027.3, 2차 활용 대부분 2029 적용. 미국 TEFCA 문서 교환이 2025년 이전 약 1천만 건에서 2025년 말 약 4.64억 건으로 늘었고, 개인 접근 서비스(IAS)가 개통됐다. CMS 환자 접근 API 지표 보고가 2026 시작. 한국 건강정보 고속도로 참여 의료기관 1,263곳(상급종합병원 47곳 전체) | 닫힘: **동의 없는 민감 데이터 거래.** FTC가 Kochava, Gravy Analytics 등에 민감 위치·건강 데이터 거래 금지 명령을 냈다. 열림: **사람이 병원·기기에서 자기 기록을 꺼내 오는 길.** 다만 그걸 회차·용도별로 동의해 연구에 기여하고 보상받는 레일은 없다 |
| **3. 에이전트가 지갑을 가졌다** | x402 on Base 누적 1.38억 건(2026 3Q), 87%가 $0.0001~0.10. XRPL 에이전트 거래 누적 약 1,350만 건, x402 판매자 168곳(보도 기준). x402 재단 출범, AP2 같은 에이전트 결제 표준 | 닫힘: 사람이 계약서와 카드로 하는 결제의 하한($0.30 고정 수수료, 80일 계약). 열림: **기계가 작은 거래를 자주** 하는 것 |

출처: [Epoch AI](https://epoch.ai/blog/will-we-run-out-of-data-limits-of-llm-scaling-based-on-human-generated-data), [Media and the Machine](https://mediaandthemachine.substack.com/p/ai-content-licensing-deals-june-2026), [Sidley (EHDS)](https://www.sidley.com/en/insights/newsupdates/2025/01/european-health-data-space-regulation-adopted-what-next-for-life-sciences-companies), [McCann FitzGerald (EHDS)](https://www.mccannfitzgerald.com/knowledge/data-privacy-and-cyber-risk/ehds-regulation-secondary-use-of-electronic-health-data), [healthit.gov (TEFCA)](https://healthit.gov/resources/data-liquidity-affordability-and-access-the-history-growth-of-tefca/), [CMS Patient Access API](https://cms.gov/priorities/key-initiatives/burden-reduction/interoperability/frequently-asked-questions/patient-access-api), [데일리팜 (건강정보 고속도로)](https://www.dailypharm.com/user/news/36789), [The Record (Kochava)](https://therecord.media/ftc-bans-kochava-location-data-sales), [CyberScoop (Gravy)](https://cyberscoop.com/ftc-data-broker-action-gravy-analytics-venntel-mobilewalla/), [Cointelegraph (x402 Base)](https://cointelegraph.com/news/agentic-payment-activity-surpasses-100m-transactions-on-base), [Yellow (XRPL)](https://yellow.com/news/ai-agents-13m-payments-xrp-ledger)

**세 흐름이 겹치는 빈자리:** 사람이 꺼낼 권리가 생겼고(2), 그 데이터의 값이 올랐고(1), 기계가 작은 거래를 할 수 있게 됐다(3). 그런데 **"사람의 에이전트가 회차마다 동의하고, 라이선스를 걸고, 직접 보상받는" 레일이 없다.** AgentRail이 그 레일이다.

## 3. 어느 시장에서 무엇이 바뀌나

| 시장 | 지금 | AgentRail 이후 | 바뀌는 숫자 |
|---|---|---|---|
| **임상·코호트 연구** | 빠진 주차가 생기면 사람을 더 뽑는다(1명 $2,273~6,533). 데이터 접근은 중앙값 80일 | 연구 에이전트가 빠진 사람-주를 찾아 그 사람에게 참여를 요청하고, 그 주에 채운다 | 빈칸 비용: 재모집 $2,000대 → 참여자-주 $20 (추정). 리드타임: 80일 → 회차 단위(분) |
| **제약 RWE** | 중개사가 비식별 대량 데이터를 묶음으로 판다. 동의 범위와 출처 추적이 약하다 | 회차별 동의 해시와 라이선스가 기록마다 원장에 붙는다. 철회하면 라이선스가 회수된다 | 감사 가능성: "계약서상 동의" → 기록 단위로 검증되는 동의 |
| **헬스케어 AI 학습·평가** | 공개 데이터는 바닥나고, 비공개 데이터는 큰 계약으로만 산다 | 동의받은 종단 기록을 사람-주 단위로 라이선스. 용도는 DUO 코드로 제한 | 거래 단위: 수년·수천만 달러 계약 → 사람-주·수십 달러 |
| **웨어러블·디지털 헬스** | 기기 데이터는 기업 서버에 갇히고, 사용자는 5.5일이면 떠난다 | 사용자가 자기 기록으로 연구에 기여하고 보상받는다. 보상은 참여 유지 기간을 늘린다(약 22일, Pratap 2020) | 데이터 원천이 사용자의 에이전트로 이동 |
| **데이터 브로커** | 동의 불분명한 대량 재판매, 규제로 닫히는 중 | 동의 기반 대체재. 규제가 강해질수록 유리해진다 | "동의 없는 $300B 시장" 중 민감 데이터부터 대체 |
| **사람 (데이터 원천)** | 1인당 $17(파산 경매), 1회 $25 | 회차마다 직접 보상, 라이선스 소유자, 언제든 중단·철회 | 받는 쪽: 0 → 기여할 때마다 |

## 4. 왜 사람 단위 건강 기록부터인가 (독보성)

| 이유 | 설명 |
|---|---|
| 값이 가장 높다 | 한 사람의 여러 출처 종단 기록은 대량 레코드보다 연구 가치가 높고, 대체할 공급원이 없다 |
| 경계가 가장 어렵다 | 동의, 재식별, 철회가 다 걸린다. 여기를 통과한 엔진은 기업 간 데이터(동의 층이 가벼움)로 그대로 내려간다. 반대 방향은 안 된다 |
| 규제가 해자가 된다 | EHDS·FTC·개인정보보호법이 강해질수록 회차별 동의 기록, 감사 로그, 검증 기관 Credential 네트워크를 가진 쪽이 유리하다. 단순 x402 데이터 마켓은 여기 못 들어온다 |
| 네트워크가 쌓인다 | 검증된 연구 기관(Credential), 참여자의 동의 이력, 출처 기관(병원 내보내기 API) 연결이 쌓일수록 새 연구가 붙기 쉬워진다 |
| 공급 경로가 있다 | 우리 참여자 앱과 연구자 워크스페이스가 실제 연결 대상이다(README 12절). 웨어러블 출하 연 6.1억 대, 미국 성인 46% 보유 |

## 5. 왜 XRPL인가

| 필요 | XRPL 기능 | 다른 방법이면 |
|---|---|---|
| 기여가 확인될 때만 보상, 철회하면 환불 | 열쇠 공개형 Escrow (Testnet 증거) | 별도 에스크로 서비스와 계약 |
| 양도 불가, 회수 가능한 연구 라이선스 | MPT + Clawback (Testnet 증거) | 중앙 DB 권한, 외부에서 검증 불가 |
| 검증된 기관만 참여자에게 지급 | Credential + DepositPreauth (Testnet 증거) | 플랫폼 KYB, 플랫폼을 믿어야 함 |
| 에이전트가 예산을 혼자 못 올림 | 다중서명 (Testnet 증거) | 내부 승인 시스템 |
| 사람-주 단위 소액 정산 | 건당 약 $0.00002, 3~5초 | 카드 $0.30 + 2.9%, 영업일 정산 |

## 6. 피치 (영상 60초)

1. "데이터는 연 3천억 달러 넘게 거래된다. 그런데 그 데이터를 만든 사람은 거래에 없다. 23andMe 1,500만 명의 유전 정보는 1인당 17달러에 경매됐다."
2. "지금 세 가지가 동시에 바뀐다. AI는 공개 데이터를 다 써 가고, 법은 사람에게 자기 기록을 꺼낼 권리를 주고, 에이전트는 지갑을 가졌다."
3. "그래서 다음 데이터 시장은 사람이 자기 에이전트로 참여하는 시장이다. 가장 비싸고 가장 어려운 데이터가 한 사람의 종합 건강 기록이다."
4. "지금 연구는 빠진 몇 주를 채울 방법이 없다. 사람을 다시 모으는 데 2천 달러가 넘고, 데이터 하나 받는 데 80일이 걸린다."
5. "AgentRail에서는 연구 에이전트가 빠진 사람-주를 찾아 참여를 요청한다. 그 사람의 에이전트가 동의한 만큼만 기여하고, XRPL이 동의·라이선스·보상을 한 번에 묶는다. 3초, 0.00002달러."
6. "가장 어려운 경계를 먼저 풀었다. 같은 엔진이 AI 학습 데이터와 로봇 데이터에서도 돈다."

## 7. README용 영문 섹션 (붙여 넣기)

### Why this matters now

**Data about people is traded without the people.** The data broker market is $300–435B a year; IQVIA alone earned $16.3B in 2025. Those whose data it is get almost nothing: 23andMe's 15 million customers were auctioned for about $17 each.

**Three shifts are breaking that model at once.**
1. *The AI data wall.* Public human text runs out between 2026 and 2032 (Epoch AI). Value moves to consented, private, longitudinal data, which is why AI licensing deals went from 12 in 2023 to 28 in 2024.
2. *Data rights become law.* The EU Health Data Space is in force (2025), with secondary use from 2029. US TEFCA exchange grew from ~10M documents to ~464M in 2025, and individual access is live. Korea's health information highway connects 1,263 hospitals. Meanwhile the FTC is banning brokers from selling sensitive data without consent.
3. *Agents have wallets.* x402 passed 138M payments on Base, 87% under 10 cents. XRPL agent payments passed 13.5M (reported).

**The gap where they meet:** people can now pull their own records, those records are worth more than ever, and machines can make small, frequent payments. But there is no rail for a person's agent to consent per round, attach a revocable licence and be paid per contribution. AgentRail is that rail. It starts with the hardest case, one person's longitudinal health record, and extends to AI training data and B2B data by lightening the consent layer.

| Market | Today | With AgentRail |
|---|---|---|
| Clinical and cohort research | missing weeks mean re-recruiting at $2,273–6,533 per person; data access takes a median of 80 days | the study's agent requests exactly the missing person-weeks; ~$20 per person-week (estimate), settled in seconds |
| Pharma real-world evidence | bulk de-identified data with weak consent provenance | consent hash and revocable licence on every record |
| Health AI training and evaluation | multi-year, multi-million licences | person-week licences limited by DUO purpose codes |
| Wearables and digital health | data locked in vendor servers; median retention 5.5 days | users contribute their own records and are paid per round |
| People | ~$17 (auction), $25 one-off | paid each round, own the licence, can stop or revoke any time |

## 8. 남은 확인

- Grand View AI 학습 데이터 숫자와 XRPL 1,350만 건은 원문 미확인이다. 보도 기준으로 적는다.
- EHDS의 2031년 적용 범위는 자료마다 다르다. 피치에서는 "2차 활용 대부분 2029"만 쓴다.
- 데이터 브로커 시장 규모는 정의 차이가 크다. 피치에서는 "연 3천억 달러 이상"(가장 낮은 추정 기준)으로 쓴다.
- "의료 데이터가 세계 데이터의 30%"라는 통계는 1차 출처가 불분명하니 쓰지 않는다.
