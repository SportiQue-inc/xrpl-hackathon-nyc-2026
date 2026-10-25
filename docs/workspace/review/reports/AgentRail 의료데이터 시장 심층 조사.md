# 건강데이터 시장에 사람을 거래 당사자로 세운다

기준일은 2026년 10월 25일이다. 결론부터 말하면, 사람 한 명의 종단 건강 기록은 데이터 시장 전체에서 가장 비싸게 팔리는 자산이다. 그런데 그 기록의 주인은 지금 어느 거래에도 당사자로 들어가 있지 않다. Flatiron이 인수될 때 큐레이션된 종양 환자 기록 한 명분은 약 $1,000으로 평가됐고, 데이터 브로커의 레코드는 장당 $0.05~0.20에 팔린다. 그 사이 어느 거래에서도 기록 주인에게 돌아간 몫은 사실상 0%였다. 2026년에는 네 가지 흐름이 한꺼번에 겹친다. AI 기업은 공개 데이터를 거의 다 썼고, 미국·EU·영국·한국은 사람이 자기 기록을 꺼내 올 권리를 법과 인프라로 만들었다. 동의 없이 모은 민감 데이터는 FTC 명령, DOJ 규칙, 한국 개인정보위의 수천억 원 과징금 때문에 비싸지고 있다. 그리고 에이전트가 소액 결제를 할 수 있는 표준(x402 재단)과 원장 기능(XRPL의 Credentials, MPT, TokenEscrow)이 2025~2026년에 실제로 가동됐다. 그런데 다섯 나라 어느 제도에도 "사람이 연구마다, 회차마다 동의하고 그 대가를 직접 받는" 레일은 없다. AgentRail은 바로 그 레일이다. 다만 숫자 대부분은 2차 자료이고, 사람들이 실제로 참여할지(돈을 줘도 37.8%는 거절한다)와 에이전트 결제 거래량의 질은 아직 열린 질문이다. 아래에서 각각 근거를 단다.

표시 규칙: **(2차)** 2차 보도나 검색 요약으로만 확인한 숫자. **(미확인)** 출처끼리 충돌하거나 원문을 확인하지 못한 숫자. **(파생)** 공개 숫자로 우리가 계산한 값. **(추정)** 우리 가정. 조사 노트 대부분이 검색 요약을 바탕으로 했으므로, 피치에 넣기 전에 링크를 한 번씩 눌러 확인하는 것이 좋다. 출처가 불분명한 "의료 데이터가 세계 데이터의 30%" 같은 통계는 쓰지 않았다.

## 테제: 가장 비싼 데이터의 주인이 거래에서 빠져 있다

지금 건강데이터 경제는 사람에 관한 데이터를 그 사람 없이 거래하는 구조다. 미국 HIPAA에서는 식별자 18개를 지운 비식별 데이터를 환자 동의나 보상 없이 팔 수 있다 ([Medical Economics](https://www.medicaleconomics.com/view/who-profits-from-medical-records-), 2차). 그래서 가치는 중개 단계마다 쌓인다. IQVIA는 2025 회계연도 매출이 **$16.31B**였고, 그중 데이터·분석 부문(TAS)만 **$6.626B**였다 ([IQVIA FY2025](https://www.iqvia.com/newsroom/2026/02/iqvia-reports-fourth-quarter-and-full-year-2025-results-issues-full-year-2026-guidance), 2026, 1차). 토큰화로 사람 단위 기록을 잇는 Datavant는 2021년 **$7.0B**로 평가됐다 ([BusinessWire](https://www.businesswire.com/news/home/20210609005224/en), 2021, 1차). 병원도 몫을 챙기기 시작했다. Truveta는 Regeneron에게서 **$119.5M**을 투자받고 엑솜 연계 EHR의 독점 접근권을 넘겼다 ([Fierce Biotech](https://www.fiercebiotech.com/medtech/jpm25-regeneron-illumina-and-more-back-truveta-10m-genome-sequencing-project), 2025, 2차). Oracle은 회원 병원이 제약 연구로 수익을 낼 수 있다고 홍보한다 ([Oracle LHN](https://www.oracle.com/life-sciences/learning-health-network/), 1차). 그런데 이 거래들 어디에도 기록 주인에게 돈이 간다는 조항은 없다.

공급 방식은 두 가지로 굳어 있다. 동의가 불분명한 대량 재판매, 그리고 몇 년짜리 대형 양자 계약이다. 연구에 실제로 필요한 단위는 "특정한 사람들의 특정한 몇 주"인데, 이 단위로는 거래가 아예 성립하지 않는다. AgentRail은 이 빈자리를 메운다. 사람의 에이전트가 회차별·용도별로 동의하면, XRPL이 기록마다 동의 해시와 연구 라이선스(MPT, 철회하면 회수)와 보상(Escrow)을 묶는다. 이 구조는 가장 어려운 데이터에서 먼저 성립해야 한다. 재식별, 철회, 규제가 한꺼번에 걸리는 사람 단위 종단 건강 기록이다. 여기서 통하는 엔진이라면 동의 층이 가벼운 AI 학습 데이터나 기업 간 데이터로는 그대로 내려갈 수 있다.

## 데이터 시장 전체 지도

시장조사 회사들은 정의가 서로 달라서 같은 시장인데도 값이 2~10배씩 벌어진다. 그래서 아래 표는 범위로 적었고, 확인할 수 있는 곳은 실제 기업 매출을 함께 적었다.

| 층 | 규모 (연도) | 돈이 가는 곳 | 사람 몫 | 출처 |
|---|---|---|---|---|
| 데이터 브로커 전체 | 2025년 $298B~434B (2차, 정의 차이 큼) | 수집·재판매 사업자 | 없음 | [SNS Insider](https://www.snsinsider.com/press-release/global-data-brokers-market), [Knowledge Sourcing](https://www.knowledge-sourcing.com/resources/press-releases/data-broker-market), [TBRC via GII](https://www.gii.tw/report/tbrc1730822-data-broker-global-market-report.html) |
| 임상시험 | 2025년 $65B~89B (2차). 신규 시작 연 35,338건 (2022) | CRO, 제약, 연구기관 | 방문당 사례비 | [Fortune BI](https://www.fortunebusinessinsights.com/markt-f-r-klinische-studien-106930), [Research and Markets](https://www.researchandmarkets.com/reports/4396385/clinical-trials-market-size-share-and-trends), [Preprints.org 2024](https://www.preprints.org/manuscript/202409.0559) |
| 제약 RWD·RWE | IQVIA TAS $6.626B, Tempus 데이터 $316.4M (2025 실적, 1차). "RWE 솔루션" 시장 추정 $2.0B~20.03B (2025, 2차) | 중개사, 토큰화 회사, 병원 컨소시엄 | 0% | [IQVIA](https://www.iqvia.com/newsroom/2026/02/iqvia-reports-fourth-quarter-and-full-year-2025-results-issues-full-year-2026-guidance), [Tempus](https://www.tempus.com/news/pr/tempus-reports-fourth-quarter-and-full-year-2025-results/), [IMARC](https://www.imarcgroup.com/real-world-evidence-solutions-market), [Fortune BI](https://www.fortunebusinessinsights.com/markt-f-r-reale-evidenzl-sungen-107676) |
| 헬스 AI | 시장 추정 2025년 $21.66B, 2030년 $110.61B. 실제 지출 2025년 $1.4B (Menlo, 2차) | AI·의료 SW 기업 | 없음 | [MarketsandMarkets](https://www.marketsandmarkets.com/PressReleases/artificial-intelligence-healthcare.asp), [eWeek/Menlo](https://www.eweek.com/artificial-intelligence/healthcare-ai-spending/) |
| AI 학습·평가 데이터 | 데이터셋 시장 2024년 $2.68B, 2030년 $11.16B (2차). 전문가 데이터 기업 Mercor 연환산 약 $2B (2026.6, 총거래액), Surge 약 $1.2B (2024) (2차) | 라벨링·전문가 중개 | 시급 (의사 $120~300/시간) | [Mynewsdesk/M&M](https://www.mynewsdesk.com/in/business-inside/pressreleases/ai-training-dataset-market-3132595), [Sacra Mercor](https://sacra.com/c/mercor/), [Contrary](https://research.contrary.com/company/surge-ai), [Mercor 공고](https://work.mercor.com/jobs/list_AAABl5_20bBT9868jENPlLVN/senior-attending-physician-mds) |
| 웨어러블·디지털 헬스 | 출하 6.115억 대 (2025, IDC). Oura 9개월 매출 $1.21B (2026.6까지, 2차). 디지털 바이오마커 $4.31B~6.29B (2025, 2차) | 기기·구독 회사 | 없음 (데이터는 회사 서버) | [IDC](https://www.idc.com/promo/wearablevendor/vendor), [Forbes AU](https://www.forbes.com.au/?p=207282), [MarketsandMarkets](https://www.marketsandmarkets.com/Market-Reports/digital-biomarker-market-7725399.html) |
| 공공 코호트 | All of Us 약 $153M (FY2026, 2023년 대비 약 72% 감액, 2차). 영국 HDRS £600M. 한국 바이오빅데이터 1단계 ₩606.6B~660B (미확인) | 운영기관, 연구자 | 1회 $25 또는 무보상 | [CASRAI](https://casrai.org/news/nih-all-of-us-pediatric-enrollment-funding-2026), [Research Professional](https://www.researchprofessionalnews.com/rr-news-uk-innovation-2025-4-pm-announces-600m-health-data-research-service/), [전자신문](https://www.etnews.com/20261015000307) |
| 데이터를 만든 사람 | 23andMe 고객 1인당 약 $20 (파생). All of Us 방문당 $25 | 거의 없음 | 위 모든 거래에서 0% | [MedTech Dive](https://www.medtechdive.com/news/judge-approves-23andme-sale-wojcicki-TTAM/752225/), [Yale Medicine](https://yalemedicine.org/clinical-trials/all-of-us) |

이 표에서 읽을 점은 셋이다. 첫째, 돈은 연 수천억 달러 단위로 돌지만 데이터의 원천인 사람은 거래 당사자가 아니다. 둘째, 시장조사 숫자보다 기업 실적이 더 믿을 만하다. IQVIA TAS 하나가 좁게 정의한 "RWE 솔루션" 추정치의 세 배를 넘는다. AI 데이터도 마찬가지다. Scale, Surge, Mercor, Handshake의 총매출을 합치면 2025~2026년 연환산 $5B를 넘어서(2차), 데이터셋 시장 추정치보다 크다. 셋째, 공공 코호트의 돈줄은 약해지고 있다. All of Us 예산은 2023년 $500M 이상에서 2025년 약 $150M으로 줄었다 ([GenomeWeb](https://genomeweb.com/sequencing/all-us-research-program-unfazed-funding-cuts-lays-out-plans-through-2026), 2025, 2차). 사람이 직접 참여하고 산업계가 비용을 내는 모델이 들어설 여지가 그만큼 커졌다.

## 왜 지금: 2025~2026년에 네 가지 구조가 한꺼번에 바뀌었다

### AI의 데이터 벽 때문에 프런티어 랩이 동의받은 개인 기록을 찾기 시작했다

Epoch AI는 품질 기준을 넘는 공개 텍스트를 약 300조 토큰(90% 신뢰구간 100조~1,000조)으로 추정한다. 그리고 2026년에서 2032년 사이에 이 재고를 다 쓸 것으로 본다 ([Epoch AI](https://epoch.ai/blog/will-we-run-out-of-data-limits-of-llm-scaling-based-on-human-generated-data), 2024). 2026년 10월인 지금은 이미 그 구간 안이다. 합성 데이터로 이 벽을 메우기도 어렵다. 실제 데이터 없이 합성 데이터만으로 학습하면 붕괴를 피할 수 없고, 실제 데이터를 섞어야 버틴다 ([Seddik et al., arXiv 2404.05090](https://arxiv.org/html/2404.05090v1), 2024). 그러니 검증된 실제 임상 데이터는 계속 필요하다.

2026년 1월에는 두 프런티어 랩이 같은 방향으로 움직였다. OpenAI는 병원, 검사실, 웨어러블 기록을 한 사람 단위로 모으는 4인 스타트업 Torch를 ChatGPT Health용으로 인수했다. 인수가는 보도마다 $60M~100M으로 다르다 ([TechCrunch](https://techcrunch.com/2026/01/12/openai-buys-tiny-health-records-startup-torch-for-reportedly-100m/), 2026, 2차, 미확인). Anthropic은 Claude for Healthcare를 내놓으면서 HealthEx를 통해 사용자가 자기 의료 기록을 연결할 수 있게 했다 ([Techstrong.ai](https://techstrong.ai/features/anthropic-launches-claude-for-healthcare-as-openai-acquires-medical-data-startup/), 2026, 2차). 두 회사 모두 병원에서 대량 EHR을 사는 대신 환자가 직접 동의해 연결하는 길을 골랐다. 반면 공개 AI 콘텐츠 라이선스 계약은 2023년 12건에서 2025년 말까지 누적 91건에 그쳤고, 대부분 Reddit-Google(연 약 $60M) 같은 큰 양자 계약이다 ([LLM Pulse](https://llmpulse.ai/blog/ai-content-licensing-deals/), 2026, 2차). 2026년에는 계약 구조도 정액에서 사용량 기반으로 옮겨 가고 있다. Reddit CEO는 갱신 협상에서 사용량 기반 요금을 요구했다 ([CJR](https://cjr.org/analysis/reddit-winning-ai-licensing-deals-openai-google-gemini-answers-rsl.php), 2026, 2차). 작은 단위로 자주 거래하는 쪽으로 시장이 기울고 있다는 신호다.

### 사람이 자기 기록을 꺼낼 권리가 법과 인프라가 됐다

미국 TEFCA는 2023년 12월 가동한 뒤 7만 곳 이상에서 **4.74억 건** 넘는 문서를 교환했다 ([ASTP TEFCA 발표자료](https://healthit.gov/wp-content/uploads/2026/02/2026-02-19_TEFCA_Updates_Presentation_508.pdf), 2026.2, 1차 URL, 요약만 확인). 개인 접근 서비스(IAS) 운영 절차 v3.0은 2026년 8월 3일 시행됐다 ([RCE SOP](https://rce.sequoiaproject.org/wp-content/uploads/2026/07/SOP-IAS-XP-v3_June2026_Clean_-5081.pdf), 2026). 앱으로 기록에 접근하는 미국인은 2020년 38%에서 2024년 57%로 늘었다. 그런데 여러 포털을 한데 모아 주는 앱을 쓰는 사람은 **7%**뿐이다 ([ASTP Data Brief 77](https://www.healthit.gov/wp-content/uploads/2025/07/2024-HINTS-Patient-Access-DB77_508.pdf), 2025, 1차 URL). 59%가 포털을 여러 개 쓰면서도 7%만 모아 본다는 이 격차가 개인 에이전트가 들어갈 자리다. EU 건강데이터공간(EHDS)은 2025년 3월 관보에 실렸고 2027년 3월 26일부터 일반 적용된다 ([Arnold & Porter](https://www.arnoldporter.com/en/perspectives/advisories/2025/03/european-health-data-space-regulation-published), 2025, 2차). 영국 NHS App 등록자는 3,931만 명이다 ([NHS England Digital](https://digital.nhs.uk/data-and-information/publications/statistical/nhs-app-statistics/september-2026), 2026.9, 1차 URL). 한국은 2026년 2월 시행령 개정으로 마이데이터 전송요구권을 전 분야로 넓혔고, 전송 의무는 2027년 2월 20일부터 생긴다 ([바이라인네트워크](https://byline.network/2026/03/11-633/), 2026, 2차).

### 동의 없는 공급은 이제 비용이 됐다

미국 FTC는 2024~2026년에 X-Mode, InMarket, Gravy, Mobilewalla, Kochava에 민감 위치 데이터 판매를 금지하거나 제한했다. 의료기관 방문 기록이 그 핵심이다. 명령에는 공급자가 동의를 받았는지 검증하는 프로그램과 오염된 데이터 삭제가 들어간다 ([Hunton](https://www.hunton.com/privacy-and-cybersecurity-law-blog/ftc-finalizes-orders-against-data-brokers-over-sensitive-location-data), 2025; [White & Case](https://www.whitecase.com/insight-alert/ftc-settles-data-broker-kochava-over-sale-sensitive-location-data-key-takeaways), 2026, 2차). 사실상 데이터를 사는 쪽에 출처를 증명하라고 요구하는 셈이다. DOJ의 대량 민감데이터 규칙은 미국인 100명이 넘는 유전체 데이터의 우려국 이전을 제한한다. 가명처리하거나 암호화한 데이터도 여전히 규제 대상이다 ([Baker Donelson](https://www.bakerdonelson.com/doj-bulk-data-rule-key-takeaways-for-health-care-and-life-sciences), 2025, 2차). 캘리포니아 DROP은 2026년 8월부터 브로커가 45일마다 삭제 요청을 처리하도록 의무화했다 ([Malwarebytes](https://www.malwarebytes.com/blog/news/2026/08/californians-can-tell-data-brokers-to-drop-their-information), 2026, 2차).

한국 개인정보위는 2026년 6월 쿠팡에 총 **₩624.7B**의 과징금을 부과했다. 그중 **₩201.1B**는 법적 근거 없이 1,000만 명 넘는 회원의 행태정보를 수집한 데 대한 것이다 ([헤럴드경제](https://www.heraldk.com/article/2026061018420873935), 2026, 2차). AI 쪽에서도 같은 압력이 생겼다. Bartz v. Anthropic 합의는 저작물 1건당 약 $3,100, 총 **$1.5B**로 2026년 7월 최종 승인됐다 ([Authors Guild](https://authorsguild.org/news/court-grants-final-approval-anthropic-copyright-settlement/), 2026). 출처가 불분명한 학습 데이터에 이제 가격표가 붙은 셈이다. EU AI Act 제10조는 고위험 AI의 데이터 출처 관리를 요구하는데, 시행이 2027년 12월로 미뤄졌어도 방향은 바뀌지 않았다 ([Gibson Dunn](https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/), 2026, 2차).

### 에이전트가 소액을 결제할 수 있게 됐다

x402 재단은 2026년 4월 Linux Foundation 산하에서 출범했다. 주요 회원에는 AWS, American Express, Google, Mastercard, Stripe, Visa가 있다 ([Coinbase CDP 문서](https://docs.cdp.coinbase.com/x402/support/x402-foundation), 2026, 요약만 확인). Ripple도 회원으로 보도됐다 ([The Defiant](https://thedefiant.io/news/infrastructure/coinbase-x402-payment-protocol-moves-to-linux-foundation), 2차). XRPL에는 2025년 9월 Credentials, 2025년 10월 MPT, 2026년 2월 TokenEscrow와 PermissionedDomains가 메인넷에서 활성화됐다 ([xrpldashboard](https://xrpldashboard.com/amendments), 2026.10, 2차). TokenEscrow 덕분에 RLUSD 같은 토큰도 조건부 에스크로에 넣을 수 있게 됐다. 미국 GENIUS Act는 2027년 1월 18일 시행되고, OCC 최종 규칙은 2026년 10월 21일에 나왔다 ([CoinDesk](https://www.coindesk.com/policy/2026/10/21/occ-s-final-rule-to-start-fresh-in-weighing-stablecoin-rewards-against-genius-act-ban), 2026). 규제된 달러 정산 수단이 건강데이터 같은 규제 시장에도 들어올 수 있게 되는 시점이다.

이 네 흐름이 겹치는 곳에 빈자리가 하나 남는다. 사람은 자기 기록을 꺼낼 수 있게 됐고, 그 기록의 값은 올랐고, 동의 없는 공급은 막히고 있고, 기계는 작은 금액을 정산할 수 있게 됐다. 그런데 다섯 나라 어느 제도에도 개인이 연구마다 동의하고 보상받는 장치는 없다. 미국 IAS도 기록을 개인에게 전달하는 데서 멈춘다 ([ASTP](https://healthit.gov/resources/data-liquidity-affordability-and-access-the-history-growth-of-tefca/), 요약만 확인).

## 국가별 제도: 다섯 나라 모두 꺼낼 권리는 키우지만 보상 레일은 없다

| 국가 | 개인이 기록을 꺼내는 길 | 2차 활용의 기본 원리 | AgentRail을 가능하게 하는 것 | 막거나 늦추는 것 |
|---|---|---|---|---|
| 미국 | HIPAA 접근권(30일, 15일로 단축 제안 중). 정보차단 위반 건당 최대 $1M 제재. TEFCA QHIN 11곳, 문서 4.74억 건, IAS 운영 ([Becker's](https://www.beckershospitalreview.com/healthcare-information-technology/ehrs/from-law-to-enforcement-how-information-blocking-went-from-policy-to-compliance-risk/), 2026, 2차; [ASTP](https://healthit.gov/wp-content/uploads/2026/02/2026-02-19_TEFCA_Updates_Presentation_508.pdf), 2026). CMS는 미국인 약 60%가 앱으로 기록을 가져올 수 있다고 발표 (정부 자체 발표, 미확인) ([CitizenPortal](https://citizenportal.ai/articles/8661642/Federal/Executive/Department-of-Health-and-Human-Services-HHS/Centers-for-Medicare-and-Medicaid-Services-CMS/HHS-CMS-leaders-mark-1-year-of-health-tech-kill-the-clipboard-push-as-patient-access-climbs-to-60), 2026) | 비식별 데이터는 동의 없이 판매 가능 | IAS로 개인 에이전트가 기록을 가져온다. FTC·주법(워싱턴 MHMDA, 코네티컷 옵트인)·DOJ 규칙이 출처 증명 수요를 만든다 | 비식별 판매가 합법이라 기존 중개사의 원가가 더 싸다. IRB의 "부당한 영향" 규범이 보상 크기를 제한한다 ([FDA 지침](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/payment-and-reimbursement-research-subjects), 2018). CFPB 브로커 규칙은 2025년 5월 철회 |
| EU | EHDS 1차 활용 접근권, 2027.3.26 일반 적용 | 동의가 아니라 데이터접근기관(HDAB)이 허가. 대부분 2029.3.26, 임상시험·유전체는 2031.3.26 적용. 개인은 옵트아웃 가능(제71조). 수수료는 HDAB와 보유기관 몫(제62조) ([Sidley](https://goodlifesci.sidley.com/2025/09/23/navigating-the-european-health-data-space-regulation-what-life-sciences-companies-need-to-know-about-secondary-use-implementation-now-a-tracking-tool-september-2025/), 2025, 2차; [streamlex Art. 62](https://streamlex.eu/articles/ehds-en-art-62/)) | GDPR 동의 기반 기여는 HDAB 경로 밖에서도 성립한다. AI Act 제10조의 출처 관리 요구. CNIL은 가명정보도 개인정보로 본다 (Cegedim €800k, 2024) ([Lefebvre Dalloz](https://open.lefebvre-dalloz.fr/actualites/droit-affaires/donnees-sante-cegedim-sante-ecope-amende-800-000-euros_f5f21113b-ce9b-4777-a2d3-31c654fec87a), 2차) | 주된 2차 활용 경로가 허가 기반이라 개인 보상 레일이 제도 안에 없다. 의료 분야 GDPR 과징금은 265건, €32.3M으로 규모가 작다 ([CMS](https://cms.law/en/int/publication/gdpr-enforcement-tracker-report/life-science-healthcare), 2026) |
| 영국 | NHS App 등록 3,931만 명, 월 로그인 9,159만 회 (2026.9) | 기관이 연구자에게 주는 구조. HDRS £600M (정부 £500M, Wellcome £100M). UK Biobank는 3년 약 £9,000 접근료 (2024, 현재 금액 미확인) | Our Future Health 250만 명 이상 등록 (목표 500만), 바우처 제도 도입 (2023.12) ([Nature Medicine](https://www.nature.com/articles/s41591-026-04602-4), 2026; [OFH](https://ourfuturehealth.org.uk/news/introducing-our-voucher-scheme-and-what-it-means-for-equality-in-health-research/), 2023) | 참여는 자원봉사이고 사용 건당 보상이 없다. 연구 접근이 HDRS로 중앙화된다 |
| 한국 | 건강정보 고속도로 EMR 연동 1,363곳, 상급종합병원 47곳 전체. 의원급은 39,160곳 중 3.07%. 나의건강기록 앱 누적 61만 1,033명 ([머니투데이](https://www.mt.co.kr/thebio/2026/10/20/2026102011104860722), 2026.10, 2차) | 데이터3법 가명정보 특례로 과학 연구에는 동의 없이 활용 가능 (2020.8 시행) | 마이데이터 전 분야 확대 시행령 (2026.2), 전송 의무 2027.2.20부터. 바이오빅데이터 약 23.8만 명 참여, 2032년 100만 명 목표 ([전자신문](https://www.etnews.com/20261015000307), 2026, 2차). 쿠팡 과징금으로 동의 없는 수집의 비용이 커졌다 | 의료 전송요구권을 명문화할 디지털헬스케어법이 4년째 계류 중 (2026.9 기준) ([MTN](https://news.mtn.co.kr/news-detail/2026092815573380395), 2026, 2차). 의원급 연동률이 낮다. 시민단체가 재식별 위험을 이유로 반대한다 |
| 일본 | 개인이 꺼내는 경로는 이번 조사에서 확인하지 못함 | 차세대의료기반법. 인정 사업자가 옵트아웃 방식으로 수집하고, 2024.4 개정으로 가명가공 정보를 허용. 가명 작성 사업자 3곳, 이용자 2곳 인정. 상위 두 사업자가 각각 약 285만 명, 216만 명 수집 (2025.7) ([내각부](https://www8.cao.go.jp/iryou/studygloup/20250903/pdf/s-4.pdf), 2025, 1차 URL) | 제도 밖에서 본인 동의를 받는 기여 경로로 대비된다 (추정) | 기관이 결정하고 환자는 거부만 할 수 있다. 개인이 고르거나 보상받는 경로가 없다 |

다섯 나라 모두 돈은 보관 기관으로 흘러간다. EU의 HDAB와 보유기관, 영국의 코호트 운영자, 일본의 인정 사업자, 미국의 중개사와 병원이다. 개인 쪽으로 돈이 가는 레일은 다섯 곳 어디에도 없다. 이 공백을 정확히 말해 둘 필요가 있다. AgentRail은 EU의 HDAB 허가나 한국의 가명정보 경로를 대신하지 않는다. 그 경로들이 다루지 못하는 데이터를 맡는다. 식별 가능한 상태로 연결된 종단 기록, 철회할 수 있는 동의, 사람이 직접 참여해야 생기는 데이터(설문, 추가 측정, 빠진 회차 보충)가 그것이다. 미국에서는 IAS와 앱 접근이 이미 돌아가고 FTC와 주법이 출처 증명을 요구하고 있어서, 가장 먼저 시장이 열릴 곳이다. 한국은 디지털헬스케어법이 통과되거나 2027년 2월 마이데이터 전송 의무가 시작되는 시점이 진입 계기가 된다.

## 시장별로 무엇이 어떻게 바뀌나

| 시장 | 지금 (숫자) | AgentRail 이후 | 바뀌는 숫자 |
|---|---|---|---|
| 임상·코호트 연구 | 환자 1명 모집에 약 $6,533, 이탈자 대체에 약 $19,533 (2015~16 기준값, 2차) ([Clinical Leader](https://www.clinicalleader.com/doc/clinical-trial-recruitment-0001)). 이탈률 15~40%. 이탈 10%마다 대체에 45일 지연 (Medidata 모델) ([Medidata](https://www.medidata.com/en/patient-dropout-calculator/)). 3상 직접비용 하루 $55,716 ([Tufts CSDD](https://csdd.tufts.edu/sites/default/files/2025-02/Aug2024%20Day%20of%20Delay%20White%20Paper%20Final.pdf), 2024). 주요 저널 RCT의 95%에 결측 데이터가 있고 중앙값은 참여자의 9% ([Bell et al.](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4247714/), 2014). 데이터 접근 중앙값 80일, 그중 계약에 35일 ([YODA](https://yoda.yale.edu/wp-content/uploads/2026/07/YODA-Project-Dashboard-Metrics-July-2026.pdf), 2026) | 연구 에이전트가 빠진 사람-주를 찾아 그 사람의 에이전트에 요청하고, 동의한 만큼만 채운다. ICH E9(R1)의 치료정책 estimand에서는 투약을 중단한 뒤의 결과 데이터도 분석에 들어간다 ([FDA E9(R1)](https://fda.gov/media/108698/download), 2021) | 빈칸 비용이 대체 모집 $19,533에서 사람-주 $20 × 26주 = $520로 내려간다 (파생·추정). 45일 지연 한 번은 3상 직접비 약 $2.5M에 해당한다 (파생). 리드타임은 80일에서 회차 단위로 줄어든다 |
| 제약 RWE | 데이터 구독 연 $0.5~5M, 전사 계약 연 $1~10M 이상, 해마다 10~30% 인상 ([IntuitionLabs](https://intuitionlabs.ai/articles/pharma-real-world-data-platforms-comparison), 2026, 벤더 블로그 추정). 청구·EHR 연계 데이터는 "골드 스탠더드"인데 구하기 어렵다 ([ISPOR 2024](https://www.ispor.org/heor-resources/presentations-database/presentation/intl2024-3896/138131), 2차). 2019~2021 FDA 승인의 약 31%가 실사용 데이터를 활용 ([PMC12593103](https://pmc.ncbi.nlm.nih.gov/articles/PMC12593103), 2차) | 기록마다 동의 해시와 철회 가능한 라이선스가 원장에 붙는다. 출처를 기록 단위로 감사할 수 있다 | "계약서에 동의가 있다"에서 "기록마다 검증할 수 있는 동의"로 바뀐다. FTC의 공급자 동의 검증, DOJ 규칙의 수령자 기록 요구에 바로 답할 수 있다 |
| 헬스 AI 학습·평가 | 공개 텍스트는 2026~2032년에 소진된다. 라이선스는 누적 91건, 대부분 연 수천만 달러짜리 양자 계약. 의사의 평가·루브릭 작업은 시간당 $120~300 ([Mercor 공고](https://work.mercor.com/jobs/list_AAABoKZfgKtRZhmavsFEsoAk), 2차). Torch 인수가 $60M~100M (2026, 미확인) | 동의받은 종단 기록을 사람-주 단위로 라이선스하고, 용도는 DUO 코드로 제한한다. 철회하면 라이선스를 회수한다 | 거래 단위가 수년·수천만 달러 계약에서 사람-주·수십 달러로 작아진다. 출처 리스크 기준점은 Bartz의 저작물당 $3,100 (2026) |
| 웨어러블·디지털 헬스 | 출하 6.115억 대 (2025). 미국 성인 46%가 보유하고 그중 83%가 주 5일 이상 착용 ([Rock Health](https://rockhealth.com/insights/whats-your-score-insights-on-wearables-and-connected-devices-from-rock-healths-2025-consumer-adoption-survey/), 2025). 그런데 웨어러블을 쓰는 임상시험은 약 2%, 평가변수로 쓰는 경우는 1% 미만 ([Applied Clinical Trials](https://www.appliedclinicaltrialsonline.com/view/why-wearable-dhts-are-bringing-more-meaningful-data-collection-to-patient-centric-clinical-trials), 2023, 2차). 원격 연구의 참여 유지 기간 중앙값은 5.5일 ([Pratap et al.](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7026051/), 2020) | 이미 착용 중인 기기의 과거 기록과 지금 기록을 그 사람이 직접 연구에 기여한다. 새 앱을 깔고 처음부터 시작하는 이탈 곡선을 피한다 | 보상은 유지 기간을 약 22일 늘리고, 임상의 소개는 약 40일 늘린다 (Pratap, 2020). 미국 웨어러블 사용자 약 1.2억 명 가운데 연구 데이터셋에 들어간 비율은 0.1% 미만 (파생) |
| 데이터 브로커 | 시장 $298B~434B (2025, 2차). 정신건강 레코드가 장당 약 $0.055~0.20, 구독 연 $75,000~100,000 ([Duke Sanford](https://techpolicy.sanford.duke.edu/data-brokers-and-the-sale-of-americans-mental-health-data/), 2023). FTC, DROP, 쿠팡 과징금으로 압력이 커지고 있다 | 민감 건강데이터부터 동의 기반 대체재가 들어간다. 규제가 강해질수록 출처를 증명할 수 있는 쪽이 유리하다 | 브로커 재고는 45일마다 삭제 요청을 받는다 (DROP). 동의 기록이 있는 데이터만 남는다 |
| 개인 | 23andMe 고객 약 $20 (파생), All of Us 방문당 $25, 중개 거래에서는 0%. 23andMe 파산 직후 약 190만 명(약 15%)이 데이터 삭제를 요청 ([PA 법무장관](https://www.attorneygeneral.gov/taking-action/ag-sunday-supports-proposed-sale-of-23andme-that-would-protect-consumers-dna-and-data/), 2025) | 회차마다 직접 보상을 받고, 라이선스를 쥐고, 언제든 멈추거나 철회한다 | 받는 몫이 0에서 기여할 때마다로 바뀐다. 기준점: 심장질환 걷기 연구 주 $14 인센티브 ([PMC6220542](https://pmc.ncbi.nlm.nih.gov/articles/PMC6220542)) |

## 한 사람의 가치 사다리: 데이터가 깊어질수록 단가가 네 자릿수 오른다

| 데이터 깊이 | 한 사람(또는 한 레코드) 단가 | 근거 | 표시 |
|---|---|---|---|
| 브로커가 파는 집계·마케팅 레코드 | 약 $0.05~0.20 | Duke 조사에서 레코드 5,000건 $275 (약 $0.055/건), 다른 브로커는 $0.06~0.20 ([Duke Sanford](https://techpolicy.sanford.duke.edu/data-brokers-and-the-sale-of-americans-mental-health-data/), 2023) | 공개 호가, 1회 조사 |
| 공공 코호트 참여 보상 | 방문당 $25 | All of Us ([Yale Medicine](https://yalemedicine.org/clinical-trials/all-of-us)) | 정해진 사례비 |
| 단일 출처 유전형 (소비자 유전체) | 고객 1인당 약 $20 | TTAM이 2025년 7월 $305M에 인수, 고객 약 1,300만~1,500만 명 ([MedTech Dive](https://www.medtechdive.com/news/judge-approves-23andme-sale-wojcicki-TTAM/752225/), 2025). Regeneron의 $256M 낙찰은 성사되지 않았다 ([Yahoo](https://www.yahoo.com/news/23andme-officially-sold-happen-customers-194104258.html), 2차) | 파생, 부실 매각 |
| 큐레이션된 종단 종양 EHR | 환자 1인당 약 $1,000 | Roche가 Flatiron을 약 $2.1B(지분 포함)에 인수, 환자 기록 200만 명 이상 ([MedCity News](https://medcitynews.com/?p=76255), 2018, 2차) | 파생, M&A 평가 |
| 참고: 유전체 생성 원가 | 엑솜 $716~4,817, 전장 $2,094~9,706 | 체계적 문헌고찰 ([Genetics in Medicine](https://www.gimjournal.org/article/S1098-3600(23)00842-0/fulltext)) | 데이터 가격이 아니라 재생산 원가 |

사다리의 맨 아래와 맨 위는 약 1만 배 차이가 난다. 맥락이 서로 다른 숫자라 직접 비교할 수는 없다. 그래도 방향은 분명하다. 출처가 많을수록, 기간이 길수록, 임상적으로 큐레이션될수록 값이 오른다. AgentRail이 거래하는 단위는 이 사다리의 위쪽이다. 사람이 동의해서 웨어러블, 병원, 설문 기록을 한 시간축에 묶은 사람-주다. 이 단위의 가치는 브로커 레코드가 아니라 Flatiron 쪽에 가깝다.

## 왜 사람 단위 종단 기록부터인가: 해자가 생기는 자리

첫째, 대체할 공급원이 없다. 청구 데이터만으로는 종단성이 끊긴다. 미국인 약 5명 중 1명이 해마다 건강보험을 바꾸기 때문이다 ([Truveta](https://www.truveta.com/?p=268697), 1차). 그래서 업계는 연계 데이터를 사려고 회사를 산다. Datavant는 Aetion을 약 $400M에 인수했고 ([Axios Pro](https://www.axios.com/pro/health-tech-deals/2025/05/20/datavant-aetion-400-million), 2025, 2차, 미확인), HealthVerity는 2026년 5월 Symphony Health를 인수하며 신원 연계층과 청구 데이터를 합쳤다 ([HealthVerity](https://healthverity.com/?p=18989), 2026, 1차). 공공 데이터셋에서도 연계가 귀하다. All of Us의 Fitbit 참여자 약 6만 명 중 EHR, 측정, 유전체, 설문이 모두 있는 사람은 **46%**뿐이다 ([RTI](https://www.rti.org/publication/the-all-of-us-research-programs-wearables-dataset), 2025). 중개사는 토큰으로 사람을 잇지만, 기록 주인은 동의 하나로 자기 기록을 이을 수 있다.

둘째, 사람을 더 뽑는 것으로는 빈칸이 메워지지 않는다. 코호트 이탈은 무작위가 아니다. 나이 많은 사람, 비백인, 남성, 저학력자, 여러 질환을 가진 사람이 더 많이 빠진다 ([PMC6258319](https://pmc.ncbi.nlm.nih.gov/articles/PMC6258319)). 새로 뽑은 참여자는 기존 코호트에 생긴 편향을 고치지 못한다. 빠진 그 사람의 그 몇 주를 그 사람이 채우는 방법밖에 없고, 그 요청을 받을 수 있는 주체는 그 사람의 에이전트뿐이다.

셋째, 규제가 강해질수록 해자가 깊어진다. FTC 명령의 동의 검증 의무, DOJ 규칙의 가명정보 포함, CNIL의 Cegedim 결정, AI Act 제10조는 모두 같은 질문을 던진다. 이 데이터를 누가, 어떤 용도로, 언제까지 쓰기로 동의했는가. 회차별 동의 해시, 철회 이력, 검증된 연구기관 Credential을 쌓아 둔 네트워크는 나중에 들어온 경쟁자가 따라 하기 어렵다. 동의 층이 없는 단순 x402 데이터 마켓은 애초에 이 시장에 들어오지 못한다.

넷째, 가장 어려운 경계를 먼저 풀면 쉬운 쪽으로는 내려갈 수 있다. 반대 방향은 안 된다. 재식별 위험, 철회, 민감정보 규제를 통과한 엔진이라면 기업 간 AI 학습 데이터나 로봇 센서 데이터에서는 동의 층만 가볍게 하면 된다.

## 왜 XRPL과 에이전트 결제가 지금 맞물리나

### 필요한 기능이 원장에 내장됐다

| AgentRail에 필요한 것 | XRPL 기능 (메인넷 활성화) | 다른 방법을 쓰면 |
|---|---|---|
| 기여가 확인될 때만 보상하고, 철회하면 환불 | Escrow, RLUSD는 TokenEscrow (2026.2.12) | 별도 에스크로 계약과 서비스 |
| 양도할 수 없고 회수할 수 있는 연구 라이선스 | MPT (2025.10), Clawback | 중앙 DB 권한이라 외부에서 검증할 수 없다 |
| 검증된 기관만 참여자에게 지급 | Credentials (2025.9.4), PermissionedDomains (2026.2.4), DepositPreauth | 플랫폼 KYB, 플랫폼을 믿어야 한다 |
| 에이전트가 혼자 예산을 올리지 못하게 | 다중서명 (2016년부터) | 내부 승인 시스템 |
| 사람-주 단위 소액 정산 | 건당 약 $0.0002 실측 보도 (기본 수수료 10 drops), 3~5초 확정 | 카드 2.9% + $0.30, 영업일 정산, 차지백 |

활성화 날짜는 [xrpldashboard](https://xrpldashboard.com/amendments)(2026.10 스냅샷)와 [xrpl.to](https://xrpl.to/insights/xrpl-amendments-explained)를 따랐다(2차). Batch 개정안은 결함이 발견돼 BatchV1_1로 다시 제출됐는데, 2026년 10월 24일 기준으로 활성화 여부가 출처마다 다르다 ([CryptoSlate](https://cryptoslate.com/how-xrpl-validators-quietly-killed-a-silent-exploit-that-could-have-drained-victim-accounts-through-transaction-fees-alone/), 미확인). 그래서 데모에서는 Batch에 기대지 않는다. Escrow, MPT, Credential, 다중서명은 이 프로젝트의 Testnet 증거로 이미 시연했다. Ripple은 2026년 6월 XRPL AI Starter Kit을 냈다. XRP·RLUSD x402 결제와 XRPL Docs MCP 서버, Claude용 스킬이 들어 있다 ([The Block](https://www.theblock.co/news/business/2026-06-10-ripple-launches-toolkit-for-agentic-payments-on-xrpl-404243), 2026). 2026년 7월 t54의 XRPL x402 퍼실리테이터는 Mastercard의 Verifiable Intent를 지원하기 시작했다. 누가 어떤 한도로 결제를 승인했는지를 결제에 붙이는 표준이다 ([Stablecoin Insider](https://stablecoininsider.org/xrpl-mastercard-verifiable-intent-agent-payments/), 2026, 2차). AgentRail의 "에이전트가 동의한 범위 안에서만 쓴다"는 설계와 같은 방향이다.

### 카드와 XRPL의 수수료 차이가 이 구조를 가능하게 한다

| 항목 | 카드 (Stripe 미국 표준 2.9% + $0.30) | XRPL |
|---|---|---|
| $20 주간 기여 1건 | $0.88, 4.4% (파생) | 약 $0.0002 (실측 보도 기준), 기본 수수료로는 약 $0.00002 |
| $2.86 일 단위 기여 1건 | $0.38, 13.4% (파생) | 약 $0.0002 |
| $0.10 요청당 결제 | $0.303, 303% (파생) | 약 $0.0002, 0.2% |
| 140만 건 정산 총 수수료 | 약 $420,000 (파생) | 약 $280 (보도) |
| 확정 | 영업일 단위, 차지백 최대 수개월 | 3~5초, 되돌릴 수 없음 |

출처: [NerdWallet (Stripe 요금)](https://www.nerdwallet.com/business/software/learn/stripe-fees), [crypto.news (140만 건 $280)](https://crypto.news/ai-agents-made-1-4m-payments-on-xrpl-total-fees-280/) (2026, 크립토 매체만), [xrpl.org 거래 비용](https://xrpl.org/transaction-cost.html). 실측 보도의 건당 약 $0.0002는 기본 수수료 10 drops(0.00001 XRP)보다 높다. 시세와 부하에 따른 수수료 상승이 반영됐을 수 있으므로, 아래 계산에는 보수적으로 $0.0002를 쓴다. PayPal 소액결제 요금(4.99% + $0.09)도 $1 미만 결제에서는 여전히 수수료가 결제액보다 크다 ([WebsitePlanet](https://www.websiteplanet.com/blog/stripe-fees/), 2차).

### 에이전트 결제 거래량은 진짜지만, 대부분은 아직 상거래가 아니다

이 부분은 정직하게 말해야 한다. x402 누적 거래는 2026년 6월 2억 건을 넘었다. 그런데 Artemis 분석으로는 그중 95% 이상이 실제 판매자와 구매자의 거래가 아닌 "프로토콜 신호" 트래픽이다 ([Yahoo Finance](https://finance.yahoo.com/markets/crypto/articles/x402-foundation-activated-27-old-152440828.html), 2026, 2차). 실제 상거래 규모는 하루 약 $28,000으로 추정된다(CoinDesk 2026.3 분석의 재인용, 원문 미확인). Chainalysis에 따르면 Base의 x402 성장은 밈코인 활동이 이끌었고 이후 정체됐다. 금액 기준으로는 $1 이상 결제가 약 95%를 차지한다 ([Chainalysis](https://www.chainalysis.com/blog/x402-agentic-payments-adoption/), 2026, 요약만 확인). 그러니까 건수는 작은 호출이, 금액은 소수의 큰 결제가 채우고 있다.

XRPL 숫자도 조건을 달아야 한다. RippleX 엔지니어링 책임자 J. Ayo Akinyele는 2026년 10월 10일, XRPL의 에이전트 x402 결제가 1,340만 건을 넘었고 원장 활동의 약 25%를 차지한다고 말했다. 2026년 7월 8일 100만 건에서 약 3개월 만에 13배가 된 셈이다. 하지만 이 숫자는 공식 RippleX 대시보드가 아니라 XRPL AI Hub 같은 제3자 트래커에서 나왔고, 크립토 매체를 통해서만 확인된다 ([KuCoin](https://www.kucoin.com/news/flash/xrp-ledger-surpasses-13-4-million-agentic-payments-milestone), [crypto.news](https://crypto.news/ex-ripple-exec-on-xrps-13m-ai-payments-whats-next/), [Yellow](https://yellow.com/news/ai-agents-13m-payments-xrp-ledger), 2026, 크립토 매체만). 보도된 정산액이 약 6,982 XRP와 12,010 RLUSD에 불과하다는 점도 건당 금액이 아주 작다는 뜻이다.

그래서 피치는 이렇게 해야 한다. "에이전트 결제 수요가 이미 크다"고 말하면 안 된다. "기계가 작은 금액을 자주, 거의 무료로 정산하는 레일이 실제로 가동됐고, 그 위에 올릴 실질 거래가 아직 부족하다"고 말해야 한다. AgentRail이 올리는 것은 신호 트래픽이 아니다. 기관이 돈을 내는 실제 연구 기여다. 카드 네트워크도 같은 방향이다. Visa, Mastercard, Google AP2, OpenAI·Stripe ACP는 2025년에 모두 에이전트 결제 표준을 냈지만, 다루는 것은 승인과 신원이지 저렴한 정산이 아니다. 그리고 이 회사들이 x402 재단 회원으로 들어와 있다 ([Digital Commerce 360](https://www.digitalcommerce360.com/2025/10/16/visa-mastercard-both-launch-agentic-ai-payments-tools/), 2025). RLUSD 시가총액은 약 $2.49B(2026.9, 크립토 매체만)이고 ([KuCoin](https://www.kucoin.com/news/flash/rlusd-market-cap-hits-2-49b-surpasses-86-growth-since-start-of-2026)), GENIUS Act가 시행되는 2027년 1월부터는 규제된 달러로 기관 정산을 받을 수 있다.

## 수익 모델: 아래에서 쌓는 계산 (전부 추정)

가정은 이렇다(추정). 기여 단위는 한 참여자의 1주 종합 기록(웨어러블, 병원, 설문)이고, 기관은 참여자-주당 **$20**를 낸다. 이 금액은 이탈자 대체 비용 $19,533의 약 1/1,000이고, 주 $14 걷기 인센티브 연구 ([PMC6220542](https://pmc.ncbi.nlm.nih.gov/articles/PMC6220542))나 All of Us 방문당 $25와 비슷한 수준이다. FDA 지침은 보상이 "연구가 진행되는 동안 쌓여야 하고 완료 여부에 달려서는 안 된다"고 하는데 ([FDA](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/payment-and-reimbursement-research-subjects), 2018), 회차별 정산이 바로 그 형태다. 수수료(take rate)는 **10%**, 나머지 90%는 참여자 보상과 데이터 보관 기관 몫이다. 기관 구독료는 연구당 연 **$12,000**(빈칸 추론 에이전트, 동의 감사 로그, MCP 접근)이다. 정산은 참여자-주 1건당 XRPL 정산 1건 이상으로 잡는다.

| 연차 | 연구 수 | 연구당 참여자 | 연간 참여자-주 | 정산 건수/년 | 기여 총액 | 수수료 10% | 구독 | 연 매출 |
|---|---|---|---|---|---|---|---|---|
| 1년차 (파일럿) | 10 | 200 | 12 | 24,000 | $0.48M | $48k | $120k | **$0.17M** |
| 2년차 | 60 | 400 | 20 | 480,000 | $9.6M | $0.96M | $0.72M | **$1.7M** |
| 3년차 | 300 | 500 | 26 | 3.9M | $78M | $7.8M | $3.6M | **$11.4M** |

3년차의 300개 연구는 해마다 새로 시작되는 임상시험 약 3.5만 건(2022년 35,338건, [Preprints.org](https://www.preprints.org/manuscript/202409.0559), 2024, 2차)의 1% 미만이다. 연 390만 건을 카드로 정산하면 수수료만 약 **$3.4M**(건당 $0.88)이 든다. 이는 수수료 수입 $7.8M의 약 44%다. XRPL로는 약 **$780**이다(건당 $0.0002, 파생). 이 차이 때문에 이 구조는 XRPL 같은 레일 위에서만 성립한다.

| 구분 | 정의 | 규모 | 근거 |
|---|---|---|---|
| TAM | AI 학습 데이터 + RWE 솔루션 + 데이터 마켓플레이스 (2025) | 약 $7B (추정, 일부 중복) | 데이터셋 시장 약 $2.7B~3.2B (2차), RWE $2.0B~2.6B ([IMARC](https://www.imarcgroup.com/real-world-evidence-solutions-market), [GMI](https://www.gminsights.com/industry-analysis/real-world-evidence-solutions-market)), 마켓플레이스 $1.5B ([Grand View](https://grandviewresearch.com/industry-analysis/data-marketplace-market-report), 2024) |
| SAM | 사람 단위 종단 건강 데이터로 연구·AI를 하는 기관 | 약 $2.5B (추정) | RWE 하단 추정 기준. IQVIA TAS $6.6B를 보면 실제 거래는 이보다 크다 |
| SOM | 3년차 바텀업 | 매출 $11.4M, 기여 총액 $78M | SAM의 약 0.5% |

확장도 같은 엔진으로 동의 층만 가볍게 하면 된다. 기업 간 AI 학습 데이터 시장(Grand View, 2030년 $8.6B, [GII](https://www.giikorea.co.kr/report/grvi1611213-ai-training-dataset-market-size-share-trends.html), 2차)의 5%가 이 레일로 오고 수수료가 3%라면 연 약 $13M이 추가된다(추정).

## 정직한 위험과 반론

**돈을 줘도 참여하지 않는 사람이 많다.** 미국 성인 약 2,020명을 조사한 Briscoe 등(2020)에서 유전 데이터를 무료로 내겠다는 사람은 11.7%, 돈을 받아야 내겠다는 사람은 50.6%, 어떤 값에도 내지 않겠다는 사람은 **37.8%**였다 ([Penn State](https://www.psu.edu/news/research/story/more-half-americans-want-money-control-exchange-genetic-data), 2020). 보상이 있으면 참여 의향이 약 12%에서 62%로 오르지만, 약 38%는 끝까지 닿지 않는다. 같은 연구에서 참여 의향을 가장 크게 올린 조건은 삭제할 권리, 수집자 밖으로 넘기지 않는 것, 재사용 전 개별 허락이었다. 이것들은 AgentRail의 철회, 용도 제한, 회차별 동의와 정확히 겹친다. 반대 증거도 있다. Rock Health 2016 조사에서는 연구용 무료 공유 의향(62%)이 돈을 받는 공유 의향(42%)보다 높았다 ([MobiHealthNews](https://www.mobihealthnews.com/news/report-consumer-adoption-digital-health-reaches-tipping-point-2016), 2016, 2차). 돈을 앞세우면 동기가 오히려 꺾일 수 있다는 뜻이다. 그래서 보상은 "데이터를 판다"가 아니라 "연구 기여에 대한 시간 보상"으로 설계해야 한다.

**기술 회사에 대한 신뢰는 낮다.** 건강데이터를 의료진과 공유하겠다는 비율은 70%인데, 헬스테크 회사와는 15%, 일반 테크 회사와는 7%다 ([MobiHealthNews / Rock Health 2022](https://www.mobihealthnews.com/news/more-consumers-are-using-digital-health-manage-complex-health-conditions-rock-health-says), 2022, 2차). 2018년에는 연구기관과 공유하겠다는 비율도 35%에 그쳤다 ([CNBC](https://www.cnbc.com/2019/02/13/consumers-dont-trust-tech-companies-with-health-data-rock-health.html), 2019, 2차). 그래서 AgentRail은 플랫폼에 대한 신뢰를 요구하지 않도록 설계했다. 지급은 Credential을 받은 연구기관만 할 수 있고, 동의와 철회는 원장에서 누구나 검증할 수 있고, 기록은 병원과 IAS 같은 기관 경로로 들어온다. 그래도 실제 참여율은 검증되지 않은 가설이다.

**동적 동의의 효과 증거는 약하다.** 2025년 신속 문헌고찰은 논문 1,611편을 검토해 12편을 포함했는데, 증거는 대부분 질적이었고 모집이나 유지에 미치는 정량 효과는 측정되지 않았다 ([Lay et al., DOAJ](https://doaj.org/article/3071e42f3eb34dde848490eab44a267d), 2025). 신뢰가 높은 EXCEED 코호트 참여자들은 동적 동의 도입을 원하지 않았다 ([Wallace & Miola](https://bmcmedethics.biomedcentral.com/counter/pdf/10.1186/s12910-021-00583-w.pdf), 2021). 따라서 "회차별 동의가 유지율을 높인다"는 주장은 가설로 제시하고, 유지율 A/B 지표로 검증해야 한다. 확실히 말할 수 있는 것은 보상(+22일)과 임상의 소개(+40일)가 유지 기간을 늘린다는 점이다 (Pratap, 2020). 동적 동의의 가치는 신뢰가 낮거나 흔들리는 곳에서 가장 크다. 상업 연구, 국경 간 이전, 그리고 23andMe처럼 회사 주인이 바뀌는 상황이다.

**사람 중심 데이터 벤처는 대부분 실패했다.** LunaDNA는 2022년 6월에 현금이 없었고 2024년 1월 31일 문을 닫았다 ([Inside Precision Medicine](https://www.insideprecisionmedicine.com/topics/precision-medicine/total-eclipse-of-lunadna-once-touted-genome-data-sharing-platform-goes-dark), 2024, 2차). Nebula Genomics는 블록체인 데이터 공유 구상에서 소비자 유전체 판매로 방향을 틀었고, $14.6M에 매각됐다 ([GenomeWeb](https://www.genomeweb.com/node/618516), 2021, 2차). Datacoup은 사용자에게 최대 월 $10을 줬지만 지금은 보이지 않는다 ([MIT Technology Review](https://www.technologyreview.com/2014/09/08/171469/datacoup-wants-to-buy-your-credit-card-and-facebook-data/), 2014). Hu-manity.co도 운영 흔적이 없다. 살아남은 MIDATA 협동조합은 개인 보상을 아예 거부한다 ([MIDATA](https://www.midata.coop/en/cooperative/), 1차). 실패의 공통 원인은 네 가지다. 사는 쪽 수요가 얇았고, 1인당 지급액이 작았고, 데이터 기여자를 모으는 비용이 컸고, 벤처 자본에 기댔다. Stanford의 Greely는 한 사람의 데이터에 가치를 귀속시키기 어렵다며 로열티 모델에 회의적이다 ([Stanford Law](https://law.stanford.edu/?p=272655), 2차).

AgentRail이 다른 점은 출발점이다. 공급을 먼저 모아 두고 살 사람을 기다리지 않는다. 기관이 이미 돈을 쓰는 문제, 곧 빠진 사람-주에서 시작한다. 연구 에이전트가 특정 빈칸을 찾고 나서야 그 사람에게 요청이 간다. 그래서 첫 거래부터 사는 쪽이 정해져 있다. 보상도 데이터의 미래 가치를 나누는 로열티가 아니다. 회차마다 정해진 기여 대가라서 귀속 문제를 피하고, FDA 보상 지침의 형태에도 맞는다. 둘째로, 기록을 플랫폼이 보관하지 않는다. 라이선스를 회수할 수 있어서 23andMe처럼 동의가 회사 자산으로 넘어가는 문제가 구조적으로 생기지 않는다. 셋째로, 정산 비용이 거의 0이라서 1인당 금액이 작아도 거래가 성립한다. LunaDNA 시절에는 없던 조건이다. 그렇다고 이 차이가 성공을 보장하지는 않는다. 기관 구매자 확보가 가장 큰 미검증 가정이다.

**제도와 경쟁 쪽 위험도 있다.** 미국에서는 비식별 데이터를 동의 없이 팔 수 있어서, 출처 증명이 필요 없는 구매자에게는 기존 중개사가 더 싸다. EU의 주된 2차 활용 경로는 동의가 아니라 HDAB 허가라서, AgentRail은 그 경로 밖의 동의 기반 기여로 자리를 잡아야 한다. 일본은 옵트아웃 방식의 기관 중심 제도다. 한국은 디지털헬스케어법이 4년째 계류 중이다. 에이전트 결제 쪽에서는 x402 거래 대부분이 신호 트래픽이고, XRPL 숫자는 제3자 트래커 기준이다. 시장조사 규모는 정의에 따라 몇 배씩 다르다. 그래서 이 문서는 기업 실적과 1차 연구를 우선했다.

## 60초 피치 (한국어)

**0~10초.** "Flatiron이 인수될 때 종양 환자 한 명의 기록은 약 천 달러로 평가됐습니다. 그 기록의 주인이 받은 돈은 0원이었습니다. 23andMe 고객 1,500만 명의 유전 정보는 파산 끝에 고객 한 명당 약 20달러에 팔렸고, 190만 명이 삭제를 요청했습니다."

**10~22초.** "2026년에 네 가지가 한꺼번에 바뀌었습니다. AI는 공개 데이터를 거의 다 썼고, OpenAI와 Anthropic은 환자가 직접 연결하는 건강 기록으로 갔습니다. 미국과 EU와 한국은 사람에게 자기 기록을 꺼낼 권리를 줬습니다. 동의 없는 데이터에는 FTC 명령과 수천억 원 과징금이 붙습니다. 그리고 에이전트는 지갑을 가졌습니다."

**22~34초.** "그런데 어느 나라에도 사람이 연구마다 동의하고 직접 보상받는 레일은 없습니다. 연구는 빠진 몇 주를 채우지 못합니다. 이탈자 한 명을 대체하는 데 2만 달러 가까이 들고, 원격 연구 참여자는 5.5일이면 떠납니다."

**34~48초.** "AgentRail에서는 연구 에이전트가 빠진 사람-주를 찾아서 그 사람의 에이전트에게 요청합니다. 사람이 동의한 만큼만 기여하고, XRPL이 기록마다 동의 해시와 철회하면 회수되는 라이선스와 에스크로 보상을 묶습니다. 주간 기여 20달러를 카드로 정산하면 88센트가 들고, XRPL로는 0.02센트도 들지 않습니다."

**48~60초.** "3년차 300개 연구에서 연 390만 건을 정산하면 매출은 1,140만 달러입니다. 가장 어려운 데이터인 한 사람의 종단 건강 기록에서 동의와 철회를 먼저 풀었습니다. 같은 엔진은 AI 학습 데이터에서도 그대로 돕니다."

## README용 영문 섹션 (붙여 넣기)

```markdown
### Why this matters now

**The most valuable health data is traded without the people it describes.** A curated oncology patient record was valued at about $1,000 when Roche bought Flatiron (2018, derived), while data brokers sell records for $0.05–0.20 (Duke, 2023). IQVIA's data and analytics segment alone made $6.6B in 2025. In none of these deals did the people whose records changed hands receive anything. When 23andMe went bankrupt, its customers' DNA was sold to TTAM for $305M (July 2025), about $20 per customer (derived), and about 1.9M people asked for their data to be deleted.

**Four shifts landed at the same time in 2025–2026.**
- *The AI data wall.* Epoch AI expects quality public text to run out between 2026 and 2032. In January 2026 OpenAI (Torch) and Anthropic (HealthEx) both turned to patient-connected records instead of bulk EHR deals.
- *People got the right to pull their records.* US TEFCA has exchanged 474M+ documents and Individual Access Services is live. The EU Health Data Space applies from March 2027. Korea's MyData transfer duty starts in February 2027. Yet only 7% of US patients use an app that aggregates their portals.
- *Non-consented supply got expensive.* FTC orders now require brokers to verify consent. The DOJ bulk-data rule covers pseudonymized genomic data. Korea fined Coupang ₩201.1B for collecting behavioral data without a legal basis. The Bartz v. Anthropic settlement put a price on unlicensed training data: $1.5B.
- *Agents can pay.* The x402 Foundation launched under the Linux Foundation in 2026, with Visa, Mastercard, Google and Stripe as members. XRPL activated Credentials, MPT and TokenEscrow between 2025 and 2026.

**The gap:** none of the US, EU, UK, Korea or Japan has a rail that lets a person consent per study, per round, and get paid directly. AgentRail is that rail. A study's agent finds the missing person-weeks. The participant's agent consents to exactly what it will share. XRPL binds a consent hash, a revocable research licence (MPT with clawback) and an escrowed payment to every record. Settling a $20 weekly contribution costs $0.88 by card and about $0.0002 on XRPL.

**Being honest about the evidence:** 37.8% of Americans would not share genetic data at any price (Briscoe 2020). Fewer than 15% trust health-tech companies with their data. Evidence that dynamic consent improves retention is still qualitative. Most x402 traffic is protocol signaling, and the 13.4M XRPL agentic payment count comes from third-party trackers. AgentRail starts from what buyers already pay for (filling missing person-weeks) rather than collecting supply first, which is where LunaDNA and similar ventures failed.

| Market | Today | With AgentRail |
|---|---|---|
| Clinical and cohort research | Replacing one dropout costs ~$19.5k; 95% of top-journal RCTs have missing outcome data; data access takes a median of 80 days | Backfill a specific person-week for ~$20 (estimate), settled in seconds |
| Pharma RWE | $0.5–5M/yr data subscriptions; linked longitudinal data is scarce | Consent hash and revocable licence on every record |
| Health AI training and eval | 91 public licensing deals in total, most of them multi-year; physicians paid $120–300/hr | Person-week licences limited by DUO purpose codes |
| Wearables | 611M devices shipped in 2025; ~2% of trials use wearables; remote studies retain participants a median of 5.5 days | People contribute the data their devices already collect; compensation adds ~22 days of retention |
| People | $0 from intermediary deals; $25 per visit | Paid each round; own the licence; can stop or revoke at any time |

Revenue (estimate): $20 per participant-week, 10% take rate and $12k per study per year. In year 3, 300 studies give 3.9M settlements, $78M of contributions and $11.4M of revenue. That is under 1% of the ~35k trials started each year. Card fees on that volume would be ~$3.4M; on XRPL they are ~$780.
```

README 영문 섹션에 나오는 숫자의 출처는 이 문서 본문의 링크와 같다. Flatiron과 23andMe의 1인당 값은 파생값이고, XRPL 13.4M과 RLUSD 숫자는 크립토 매체를 통해서만 확인했다.

## 결론

이번 조사로 바뀐 점이 하나 있다. "사람에게 돈을 주자"는 오래된 주장으로는 2014~2024년 벤처들처럼 실패한다. 2026년에 달라진 것은 사는 쪽의 사정이다. AI 랩은 환자가 직접 연결하는 기록으로 방향을 틀었고, 규제기관은 구매자에게 동의 출처를 증명하라고 요구하기 시작했고, 연구기관은 공공 예산이 줄어든 상태에서 이탈자를 2만 달러씩 들여 대체하고 있다. 그러니 AgentRail의 잠재력은 보상 그 자체보다, 구매자가 이제 피할 수 없게 된 동의 출처 증명을 기록 단위로 싸게 제공하는 데 있다. 보상은 그 증명을 만드는 사람이 계속 참여하게 하는 수단이다.

남은 검증은 두 가지다. 하나는 기관이 참여자-주당 $20를 실제로 낼지다. 이건 파일럿 연구 한 곳의 구매 의향으로 확인할 수 있다. 다른 하나는 사람들이 회차별 요청에 실제로 응할지다. 유지율 A/B 지표로 측정할 수 있다. 에이전트 결제 레일은 이미 준비돼 있다. 그 위에 신호 트래픽이 아닌 실제 거래를 올리는 첫 사례가 사람 단위 건강 기록이라면, 그 자체로 XRPL 생태계에 의미 있는 증거가 된다.
