# 공개 답변·유사 사례 (한국·몽골·미국)

> 법률 자문이 아닙니다. **공개 자료만** 썼습니다. K-DATA 상시자문처럼 제3자 공유가 제한된 자료는 뺐습니다.
> 조사 환경에서 정부 사이트 원문을 직접 열지 못해, 원문을 인용한 검색 결과로 확인했습니다. 각 항목에 확인 수준을 표시했고, 사건·의결 번호는 확인된 것이 없어 적지 않았습니다.

## 요약: 우리 설계 전체를 승인한 선례는 없다. 조각별 선례는 충분하다

공개된 승인 사례 중에 "개인이 자기 종합 건강데이터를 연구기관에 회차별로 제공하고 대가를 받는" 구조 전체를 다룬 것은 찾지 못했습니다. 샌드박스, 개인정보보호위원회, 미국 모두 마찬가지입니다. 대신 각 장치마다 가까운 선례가 있습니다.

| 우리 장치 | 가장 가까운 공개 선례 | 시사점 |
|---|---|---|
| 본인이 받은 의료기록을 제3자에게 넘기기 | 한국 ICT 샌드박스 "의료 마이데이터의 비대면진료 활용"(적극해석, 서비스 2025-05 출시). 미국 HHS OCR "Access right, health apps & APIs" FAQ(2019) | 본인 동의로 제3자에게 넘기는 경로는 인정됨. 미국에서는 본인이 고른 앱에 넘어간 뒤 HIPAA가 아니라 FTC·주법이 적용됨 |
| 의료 데이터를 기업·연구소에 제공하고 개인에게 대가 지급 | 부산 블록체인 규제자유특구 의료 마이데이터 플랫폼(2020-07, 대가 부분의 특례 범위는 미확인). 미국 LunaDNA(2018, 대가를 주식으로 지급해 SEC 증권 공모를 거침) | 대가를 지분이나 가치가 오르는 토큰으로 주면 증권 위험이 생김. **회차별 고정 금액(안정 가치)**이 안전함 |
| 연구 참여 대가와 완료 보너스 | FDA 2018 지침, SACHRP 2019 권고. 대학 IRB 정책은 제각각(Syracuse·UC Irvine·Pitt는 소액 보너스 허용, Duke는 비권장, UNMC는 금지, UNMC·UVA는 비례 지급 의무) | 숫자 상한은 없음. 유보와 보너스는 작게(10~20%) 두고, 완료한 회차는 반드시 지급함 |
| 철회 | NIH All of Us(새 이용 중단, 이미 쓴 자료는 회수 불가, 향후 이용 여부를 다시 물음). HHS FAQ 316(authorization 철회 전 의존분은 유지). 대법원 2025-07-18 SKT 가명처리 판결 | 철회 효과를 정확히 적어야 함. 한국에서는 법이 요구하는 수준을 넘는 파기를 **계약상 약속**으로 두는 것이 우리 설계임 |
| 국외 이전 고지 | PIPC 딥시크 개선권고(2025-04-23), 알리익스프레스 과징금 19.78억 원(2024-07-24). FTC Premom(2023, 중국 업체로 몰래 전송) | 회차마다 받는 기관 이름과 나라를 명시하고, 이전을 거부할 수 있어야 함 |
| 동의 방식 | FTC Flo(2021)·GoodRx·BetterHelp·Premom(2023)·Cerebral·Monument(2024) 명령 | 약관과 분리된 적극적 명시 동의. 데이터 범주·받는 자·목적을 표시해야 함. 받은 쪽에 삭제를 지시해야 함 |
| "익명" 표현 | FTC 블로그(2024-07): 해시 ID는 익명이 아님 | 가명 참여번호를 "익명"이라 부르지 않음 |
| 삭제 약속의 지속성 | 23andMe 파산 매각(2025): 30개 넘는 주가 이의를 제기했고, 인수자가 삭제·연구 거부 정책을 승계함 | 인수자도 삭제·동의 약속에 묶이게 하고, 삭제를 증명할 수 있어야 함 |
| 앱 기반 회차별 동의 | Apple Heart and Movement Study(앱 내 동의·철회, 2년마다 재동의, IRB 감독) | 회차별 동의는 실무 선례가 있음. 받는 기관마다 IRB가 필요함 |
| 연구자 접근 통제 | PIPC 사전적정성 검토 디사일로·뱅크샐러드(2024-01-24, 클린룸 안에서 암호화된 자료만 분석하고 통계만 반출) | 실서비스 전에 같은 사전적정성 검토를 신청할 수 있음 |
| 블록체인 기록 | PIPC 블록체인 개인정보 가이드라인(2026-06) | 개인정보는 오프체인에 두고 해시만 기록. 솔트를 함께 지워야 삭제로 인정. 솔트는 재사용 금지 |
| 마이데이터 전송 수신 | 보건의료 전송요구권 고시 개정(2026-03-18, 정보 제공 기관 50곳 → 387곳). 수신하려면 전문기관 지정 필요 | 당분간 "본인이 내려받아 에이전트가 넘기는" 경로를 씀 |
| 워싱턴 MHMDA | Maxwell v. Amazon(W.D. Wash. 2:25-cv-261, 2025-02-10 제기, 첫 사적 집단소송, 판결 없음) | 기관이 대가를 내는 구조는 "sale"로 다퉈질 수 있음 |
| 몽골 | 공개된 FRC·국가인권위원회 결정을 찾지 못함 | 현지 확인 필요 |

## 설계에 바로 반영할 것
1. 대가는 **회차별 고정 금액**으로만 준다. 수익 배분이나 가치가 오르는 토큰은 쓰지 않는다(LunaDNA).
2. 동의 화면은 약관과 분리하고, 회차마다 받는 기관 이름·나라·목적·항목을 표시한다. 국외 이전 거부 버튼을 둔다(FTC 명령, PIPC 딥시크·알리익스프레스).
3. 철회하면 받은 기관에 삭제 지시를 보내고 회신을 기록한다(FTC 명령, 23andMe).
4. 원장 해시에는 회차별로 다른 솔트를 쓰고, 삭제할 때 솔트도 지운다(PIPC 블록체인 가이드라인).
5. 연구 등록 시 IRB 승인 번호를 필수 입력으로 둔다.
6. 실서비스 전 PIPC 사전적정성 검토를 신청한다.

---

# 부록 A. 한국·몽골 상세 노트
# 공개 선례 조사: 한국·몽골 (개인 건강데이터 → 연구기관 기여, 회차별 동의·보상, 철회·삭제, 국외이전)

조사일: 2026-10-25. 방법: WebSearch만 사용(.go.kr 및 언론사 WebFetch는 DNS 차단으로 모두 실패). 출처는 대부분 언론·로펌 뉴스레터가 공식 발표를 인용한 것이며, 원문(의결서/보도자료)은 직접 확인하지 못함.
표시: [확인] = 복수 보도로 날짜·내용 일치 / [부분확인] = 단일 보도 또는 세부 미확인 / [미확인] = 존재·세부를 검증 못함.
K-DATA 마이데이터 상시자문 및 비공개 자료는 제외. 사건번호·의결번호는 확인된 것이 없어 기재하지 않음.

## 핵심 결론 (요약)
- 우리 설계와 같은 "개인이 자기 건강데이터를 연구기관에 직접 넘기고 회차별로 대가를 받는" 구조를 승인한 공개 규제샌드박스/PIPC 결정은 **찾지 못함**. 가장 가까운 사례는 부산 블록체인 규제자유특구 '의료 마이데이터 비대면 플랫폼'(2020.7, 환자 보상 구상)과 ICT 샌드박스 '의료 마이데이터 비대면진료 활용'(적극해석)임.
- 따라서 "선례가 있다"고 말하기보다는 "구성요소별 선례(전송요구권, 오프체인 저장·파기, 국외이전 고지/동의, 가명처리 판례, 사전적정성)"로 설계를 정당화하는 편이 정확함.

---

## 1. ICT 규제샌드박스 – 의료 마이데이터의 비대면진료 활용 (적극해석) [부분확인]
- 기관/일자: 과기정통부 제34차 ICT 규제샌드박스 심의위원회. 날짜는 보도상 명확하지 않음(2024년 지정으로 보도, 서비스 출시 2025-05-16).
- URL: https://www.dailypharm.com/Users/News/NewsView.html?ID=309568 , https://www.unicornfactory.co.kr/article/2025051610313699611
- 내용: 건강정보 고속도로(본인진료기록열람지원시스템)와 연계된 개인 의료데이터를 환자 동의하에 비대면진료 의사가 참고하도록 **실증특례가 아닌 적극해석**으로 처리. 실증 사업자 나만의닥터(메라키플레이스).
- 유사점: 환자가 건강정보 고속도로에서 받은 자기 기록을 제3자(의사)에게 동의 기반으로 넘김 → 우리 "개인 에이전트가 병원기록을 연구기관에 전달"과 구조 동일.
- 시사점: 본인 동의 기반 전달 자체는 "규제 없음/적극해석" 가능성이 높음. 단 수신자가 의료인이었고 **대가 지급은 없음**. 연구기관 수신 + 보상은 별도 쟁점.

## 2. 부산 블록체인 규제자유특구 2차 – 블록체인 기반 의료 마이데이터 비대면 플랫폼 (B-Healthy) [부분확인]
- 기관/일자: 중소벤처기업부 규제자유특구위원회, 2020-07 지정(2020-07-08 보도). 실증 개시 2021.
- URL: https://medigatenews.com/stand/21786 , https://www.fnnews.com/news/202007081516504578 , https://smartcity.go.kr/2021/12/15/부산시-부동산-집합투자-및-의료-마이데이터/ , https://www.fnnews.com/news/202007151448355949
- 내용: 세종텔레콤·에이아이플랫폼·재영소프트·부산대병원 컨소시엄. 개인 동의 의료데이터를 기업·연구소에 제공, **정보주체(환자)에게 보상**하는 체계를 목표로 제시. 개인정보는 삭제 가능한 오프체인 서버, 블록체인엔 참조값만 저장.
- 유사점: 가장 근접(동의 기반 제공 + 환자 보상 + 블록체인 + 삭제 가능 구조).
- 시사점: 특례 부여 조건(기간·규모·보상 방식 제한)은 원문 미확인. 보상 지급이 특례 대상이었는지, 사업자 계획이었는지 불분명 → 인용 시 "구상/실증"으로만 표현할 것.

## 3. PIPC 블록체인 환경 개인정보 처리 안내서(가이드라인) [부분확인]
- 기관/일자: 개인정보보호위원회, 2026-06 발표(보도 2026-06-25), 2026-07 가상자산거래소 대상 후속 안내 보도.
- URL: https://www.fnnews.com/news/202606251407435835 , https://www.blockmedia.co.kr/archives/1117558 , https://www.fnnews.com/news/202607091726066232
- 내용: 식별정보는 오프체인, 온체인엔 익명정보(해시 등)만. 파기 시 오프체인 개인정보 + **솔트 등 추가정보까지 삭제해야 파기로 인정**. 난수(솔트) 재사용 금지. 비허가형 체인은 참여자 범위·역할·책임 사전 공개. 온체인 정보를 식별정보와 함께 타 사업자에 제공 시 개인정보보호법 적용.
- 유사점: XRPL에 동의/지급 기록을 남기는 우리 설계에 직접 적용.
- 시사점: 온체인엔 연구별 가명 ID의 솔트 해시·동의 해시만 기록, 사용자별·연구별 솔트 분리, 철회 시 오프체인 데이터+솔트 삭제 → "파기" 주장 가능. 정확한 문서명은 원문 확인 필요.

## 4. PIPC 사전적정성 검토 – 디사일로·뱅크샐러드 (동형암호 통계값과 가명처리) [확인]
- 기관/일자: 개인정보보호위원회 2024-01-24 제2회 전체회의 의결(AI CCTV 건과 함께 2건).
- URL: https://m.boannews.com/html/detail.html?idx=126110 , https://newsseoul.co.kr/news/view/1065597610367852
- 내용: 마이데이터 사업자 데이터를 동형암호로 클린룸에 두고 외부 연구자는 통계분석만, 반출은 통계값만, 키는 뱅크샐러드만 보유하는 구조를 확인하고 준수방안 의결. 이행 시 중대한 사정변경 없으면 처분하지 않음.
- 유사점: 개인(마이데이터) 건강·금융 데이터를 외부 연구자가 원문 없이 활용.
- 시사점: 원본은 사용자 측(에이전트) 보관, 연구기관에는 필요 최소/집계만 → 사전적정성 검토 신청이 실무적 안전장치. 우리도 본 제도로 신청 가능.

## 5. 대법원 SKT 가명처리 정지 사건 [확인]
- 기관/일자: 대법원 1부, 2025-07-18 선고(원심 파기환송), 이후 서울고법 파기환송심 청구 기각.
- URL: https://www.tsisalaw.com/news/article.html?no=30234 , https://www.hankyung.com/article/2025080169741 , https://peoplepower21.org/?p=1996874
- 내용: 가명처리는 식별위험을 낮추는 행위로 수집·이용·제공과 구별 → 정보주체의 처리정지 요구 대상이 아님.
- 유사점: 우리 "철회·삭제" 약속과 연구기관이 이미 받은 가명데이터의 관계.
- 시사점: 법적으로는 철회 후에도 가명정보 계속 이용이 허용될 여지 → 우리는 이보다 **강한 계약상 삭제 의무**(연구기관 약정)를 두는 것이 차별점이자 신뢰 요소. "법이 요구하는 것 이상"으로 설명.

## 6. PIPC 딥시크 국외이전 시정권고 [확인]
- 기관/일자: 개인정보보호위원회 2025-04-23 제9회 전체회의.
- URL: https://www.newsis.com/view/NISX20250424_0003153087 , https://www.korea.kr/news/policyNewsView.do?newsId=156686001 , https://www.ajunews.com/view/20250428164100969
- 내용: 동의·처리방침 공개 없이 프롬프트를 중국 바이트댄스 계열사로 이전 → 합법 근거 마련, 한국어 처리방침, 파기 등 시정권고(10일 내 수락, 60일 내 이행보고). 딥시크는 이전 대상국·수령자 명시 및 국외이전 **옵트아웃** 도입 후 재개.
- 시사점: 몽골·미국 이전 시 이전국가·수령자·항목·시기·방법·보유기간을 회차 동의 화면에 명시하고 거부(이전 제외) 선택지를 제공해야 함.

## 7. PIPC 알리익스프레스 국외이전 처분 [확인]
- 기관/일자: 개인정보보호위원회 2024-07-24 전체회의(25일 발표). 과징금 19억7,800만원, 과태료 780만원, 시정명령·개선권고.
- URL: https://byline.network/2024/07/25_39282727/ , https://www.youthdaily.co.kr/mobile/article.html?no=160495
- 내용: 해외 판매자에게 이용자 정보 제공 시 동의 미취득, 이전국가·수령자 연락처 등 법정 고지사항 미고지.
- 시사점: 국외 연구기관(몽골/미국)마다 수령자 성명·연락처까지 고지 필요. 테무 건은 최종 의결 미확인[미확인].
- 참고(추가): 빗썸 2026-06-24 국외이전 별도 동의 미취득 과징금 2억1천만원 [부분확인] https://news.mtn.co.kr/news-detail/2026062516571159523

## 8. 보건의료 분야 개인정보 전송요구권 고시 (개정 2026-03-18) [부분확인]
- 기관/일자: 개인정보보호위원회(복지부 협의). 2025년 전송요구권 시행, 보건의료 고시 제정안 의견수렴 2024-11-18까지, 개정 고시 2026-03-18 발령.
- URL: https://newsseoul.co.kr/news/view/1065585620225734 , https://www.shinkim.com/kor/media/newsletter/2637 , https://www.medigatenews.com/news/1871534403
- 내용: 정보전송자 50개(질병청·건보공단·심평원·상급종합병원 47) → 종합병원 337 추가, 총 387개. 건강정보 고속도로 연계 병원부터 단계 적용. 제3자 수신자는 "개인정보관리 전문기관" 지정 체계.
- 시사점: 법정 제3자 전송을 받으려면 전문기관 지정 필요 → 해커톤 단계에선 "본인이 다운로드한 기록을 본인 에이전트가 전달"(본인 전송) 구조로 설계하고, 전문기관 지정은 로드맵으로.

## 9. 건강정보 고속도로 / 나의건강기록 앱 (복지부) [확인-제도 일반]
- URL: https://mobile.newsis.com/view/NISX20230609_0002333196 , https://www.news1.kr/amp/industry/medical/4969569
- 내용: 개인이 의료기관·공공기관 건강정보를 조회·저장·전송(본인 동의). 12개 항목(진단, 처방, 수술, 알레르기 등).
- 시사점: 우리 "병원기록" 입력원으로 정당. 연구기관 직접 전송 절차는 공개자료에서 확인 못함[미확인].

## 10. 가명정보 처리 가이드라인 2024 개정 / 보건의료데이터 활용 가이드라인 2024 개정 [확인-문서 존재, 건강 사례 세부 미확인]
- 가명정보 처리 가이드라인: PIPC 2024-02 공개(비정형데이터 기준 신설, 위험비례 샘플링 검수 허용). https://www.hwawoo.com/newsletter/2024_02_07/240207_k_i.pdf , https://www.shinkim.com/kor/media/newsletter/2342
- 보건의료데이터 활용 가이드라인: 복지부·PIPC 2024-01 개정(가명처리 FAQ Q&A 추가, 데이터심의위원회(DRB) 심의결과서 서식). https://eiec.kdi.re.kr/policy/materialView.do?num=233981 , https://www.hwawoo.com/newsletter/2024_01_25/240125_k_t.pdf
- 관련 판단 사례: 심의위가 보험사 연구 요청에 대해 "집계표로 충분 → 가명 DB 제공 부적합" 판단(날짜 미확인)[부분확인] https://medicaltimes.com/Users/News/NewsView.html?ID=1142989
- 시사점: 우리 구조는 가명정보 특례(동의 없는 이용)가 아니라 **동의 기반 제공**이므로 가이드라인은 보조 근거. 다만 연구기관 측은 DRB/IRB 심의 필요 → 연구 등록 시 IRB 승인번호 필수 필드화.

## 11. ICT 샌드박스 1호 – 휴이노 손목형 심전도 / 임상시험 참여희망자 온라인 중개 [확인]
- 기관/일자: 과기정통부 제1차 신기술·서비스 심의위원회 2019-02-14.
- URL: https://www.ajunews.com/view/20190214113720288 , https://www.dailypharm.com/user/news/77655 , https://newstomato.com/ReadNews.aspx?no=876066
- 내용: (a) 웨어러블 심전도 데이터를 의사에 전송 – 조건부 실증특례: 식약처 인증 후 개시, 2년·2,000명 이내, 진단·처방 제외. (b) 임상시험 참여자 온라인 모집 – 식약처 판단하에 온라인 모집 허용으로 규제 개선.
- 시사점: 웨어러블 데이터 전송·연구 참여자 모집 플랫폼 모두 선례 있음. 샌드박스 신청 시 예상 조건 = 기간·인원 상한, 인증/IRB 선행, 범위 제한.

## 12. 데이터 배당(경기도) / 서울시 마이데이터 [부분확인]
- URL: https://weekly.khan.co.kr/article/201912271605171 , https://golmok.seoul.go.kr/mydata/mydataPop.do
- 내용: 경기도 지역화폐 데이터 판매 수익을 사용자에게 배당(2019~2020). 서울시 마이데이터는 제3자 활용 동의 시 판매 이익 개인 지급 안내.
- 시사점: 공공에서 "데이터 제공 대가를 개인에게 지급"한 선례 존재. 다만 건강 민감정보는 아님. 보상은 "참여 사례비"로 성격 규정(생명윤리법상 연구대상자 보상 관행)하는 것이 "데이터 판매"보다 안전.

---

## 몽골
- 개인정보보호법(Law on Personal Data Protection): 2021-12-17 제정, 2022-05-01 시행. 감독: 국가인권위원회(NHRC). 국외이전은 법률·조약 근거 또는 정보주체 동의 시 허용(조문 인용은 DataGuidance 2차 자료). 건강·유전·생체정보는 민감정보로 강화 규율, 보건 분야 별도 법령이 보유·이전 제한. [확인-법령 존재]
  - URL: https://legalinfo.mn/en/edtl/16532053734461 (비공식 영문), https://www.dataguidance.com/notes/mongolia-data-protection-overview , https://nhrcm.gov.mn/en/page/40
- UN 프라이버시 특별보고관 방문(2025-04-08~14): 법은 진전이나 집행 메커니즘 보완 필요. https://www.ecoi.net/en/file/local/2124428/2025-04-14-eom-sr-privacy-mongolia.pdf [확인]
- 2026 "데이터 중개자" 개정안: 초안 단계, 시행 아님 [부분확인].
- FRC(금융규제위원회) 또는 NHRC의 건강데이터 연구·국외이전 관련 공개 결정: **찾지 못함 [미확인]**.
- 시사점: 몽골 측은 "정보주체 명시적 동의"가 국외이전 근거 → 회차별 동의에 몽골 수령기관 명시. 보건 분야 특별법(보건법 등) 확인은 현지 법률자문 필요.

## 찾지 못한 것 (명시)
- 개인 건강데이터를 연구기관에 판매/제공하고 회차별 보상하는 플랫폼에 대한 ICT/산업융합/혁신금융 실증특례 승인 공개 사례.
- PIPC의 국외이전 "중지명령"(법 28조의9) 실제 발령 사례.
- KISA/개인정보보호 포털 공식 상담사례 원문(동의 철회 시 파기: 법 제37조 1·3항 – 지체없이 복구불가 파기, 2항 예외 시 사유 통지; 민감정보 별도동의: 법 제23조 – 법조문 수준으로만 확인).
- 웨어러블 헬스케어 사전적정성 검토 사례.


---

# 부록 B. 미국 상세 노트
# US public precedents: individual-directed health-data contribution to research (compiled 2026-10-25)

Our design: an individual combines wearable data + hospital records (from the HIPAA right of access) + surveys, then contributes them to research institutions through a personal app or agent. It has per-use consent, pseudonymous study IDs, compensation per round with part held back for a quality check, withdrawal and deletion, and transfers to Korea and Mongolia.

Method: WebSearch summaries only. Direct fetches of hhs.gov, genome.gov and joinallofus.org failed with DNS errors, so the official text was not read directly. Where search summaries disagreed, I say so. "UNVERIFIED" means I did not confirm the point from a source this session.

---

## 1. HHS OCR: "The access right, health apps & APIs" FAQs (2019)
- Agency/date: HHS Office for Civil Rights (OCR), April 2019
- URL: https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/access-right-health-apps-apis/ (secondary: https://www.nixonpeabody.com/insights/articles/2019/04/22/ocr-releases-new-set-of-faqs-to-address-transmission-of-ephi-to-apps)
- What it says:
  - Under the right of access, a covered entity (CE) generally must send PHI to the app the individual designates. It cannot refuse because it doubts the app's security or how the app will use the data.
  - Once the app receives the data at the individual's direction, the CE is not liable under HIPAA for what the app does with it.
  - If the individual asks for unsecured transmission, the CE is not liable for a breach in transit. It should warn the individual of the risk.
  - An app that only facilitates the individual's access is NOT a business associate. A business-associate relationship exists only if the app was developed for the CE, or provided by or on behalf of the CE (including through the CE's EHR vendor).
  - Consumer apps that are outside HIPAA fall under the FTC.
- FAQ numbering: one NIST slide lists "FAQ 3010 Covered Entity Liability for Unsecure Transmission". I could not confirm which questions FAQs 3009, 3011 and 3012 cover (UNVERIFIED).
- Resemblance: high. The user gets hospital records into our app through the right of access, which is exactly the flow OCR addressed.
- Implication: hospitals cannot block the transfer. Our app is not a HIPAA BA as long as no hospital or EHR vendor offers it on its own behalf. We then fall under the FTC Act, the FTC Health Breach Notification Rule (HBNR) and state law instead (see items 3 and 14). If we ever partner with a hospital to distribute the app, we could become a BA.
- KR: 환자가 HIPAA 열람권으로 지정한 앱에 병원은 기록을 보내야 하고, 전달 후 앱의 사용·공개에 병원은 책임이 없음. 우리 앱은 BA가 아니라 FTC 규제 대상.

## 2. HHS: HIPAA research authorization, revocation and future use
- Agency/date: HHS OCR. FAQ 316 (undated). Interim guidance on authorizations for future research, June 2018 (21st Century Cures Act).
- URL: https://www.hhs.gov/hipaa/for-professionals/faq/316/if-a-research-subject-revokes-authorization-can-a-researcher-continue-using-information-obtained/index.html ; https://www.hhs.gov/guidance/sites/default/files/hhs-guidance-documents/hipaa-future-research-authorization-guidance-06122018%2520v2.pdf
- What it says:
  - Revoking an authorization does not undo uses already made in reliance on it (45 CFR 164.508(b)(5)(i)). PHI obtained before revocation may still be used as needed to protect the study's integrity, for example reporting adverse events, investigating misconduct, or accounting for the withdrawal.
  - Per secondary summaries of the 2018 guidance, a revocation takes effect when the CE has actual knowledge of it.
  - Per the same summaries, the guidance allows a CE to accept an oral revocation, even though the rule requires revocations in writing.
  - An authorization for future research must describe that future research well enough that a reasonable person would expect their PHI could be used for it.
  - The 2018 document is labelled interim. I did not find a final version.
- Resemblance: high for our withdrawal design ("stop future use" vs "delete what was already used").
- Implication: say plainly in the consent: withdrawal stops future rounds, and data already delivered and analysed may be kept to protect study integrity unless the institution agrees otherwise. Our model is the same reliance-exception model. When the recipient is a HIPAA CE, per-use consent sits comfortably with the authorization rules. Per-round consent also avoids the "future research description" problem.
- KR: 철회는 장래 사용만 막고, 이미 의존해 사용한 데이터는 연구 무결성을 위해 계속 쓸 수 있음(reliance exception). 동의서에 그대로 명시할 것.

## 3. FTC Health Breach Notification Rule, final amendments (2024)
- Agency/date: FTC. Voted April 26, 2024. Federal Register May 30, 2024. Effective July 29, 2024.
- URL: https://www.insideprivacy.com/health-privacy/ftc-issues-final-rule-to-expand-scope-of-the-health-breach-notification-rule/ (FTC rule at 16 CFR Part 318)
- What it says:
  - The rule explicitly covers health apps and fitness trackers.
  - A personal health record (PHR) is anything with the *technical capacity* to draw data from multiple sources.
  - A "breach" includes any disclosure without the consumer's authorization, not only hacks.
  - Persistent identifiers combined with health data count as identifiable.
  - Civil penalty is about $51,744 per violation (inflation-indexed).
- Resemblance: very high. Our app combines wearable, EHR and survey data, which is the textbook multiple-source PHR.
- Implication: we are likely a "vendor of personal health records". Any disclosure to an institution beyond what the user authorized for that round is a notifiable breach. Per-use consent records are therefore also our breach-defence evidence. Pseudonymous IDs do not take us out of scope.
- KR: 여러 소스를 결합하는 우리 앱은 HBNR상 PHR 벤더일 가능성이 큼. 동의 범위 밖 제공은 '침해'로 통지 의무 발생.

## 4. NIH All of Us Research Program (closest public analog)
- Agency/date: NIH. Running since 2018. Sample consent posted on genome.gov in 2022.
- URLs: https://joinallofus.org/what-participants-receive ; https://www.joinallofus.org/privacy ; https://www.genome.gov/sites/default/files/media/files/2022-01/Consent_to_Join_AoU_English.pdf ; https://www.researchallofus.org/frequently-asked-questions/
- What it says:
  - Payment: a one-time $25 (cash, gift card or e-voucher) when a participant visits a partner center for physical measurements and biosamples. I did not find any per-survey or per-round payments (UNVERIFIED whether any exist).
  - Data tiers:
    - Public: aggregate data.
    - Registered: individual-level, de-identified EHR, wearable, survey and physical-measurement data, available only inside the Researcher Workbench.
    - Controlled: adds genomics, unshifted dates and more demographics. Requires an institutional Data Use and Registration Agreement (DURA).
  - Access is per user with a "data passport". Researchers may not contact participants and lose access for violations.
  - Withdrawal (per search summary of the consent): the program stops new uses but cannot take back data or samples researchers already have. Old data stays available to check past studies, and name and contact details are retained. On withdrawal, participants are asked whether their data may still be used in future research.
  - Rules for non-US researcher access: not found (UNVERIFIED).
- Resemblance: very high. Wearable + EHR + surveys, coded IDs, withdrawal, return of value. The difference is that All of Us is a central NIH repository with a fixed payment, not an individual-agent marketplace paying per round.
- Implication:
  - The $25 one-time figure is the public benchmark. Per-round payments much larger than that will draw undue-influence scrutiny from IRBs.
  - Copy the tiered model, and give external researchers access in a workbench rather than as raw exports where feasible.
  - Copy the withdrawal wording ("we cannot take back what was already used").
- KR: 웨어러블·EHR·설문 결합, 코드화 ID, 철회(이미 쓴 데이터는 회수 불가)까지 가장 유사한 공공 선례. 보상은 1회 $25.

## 5. LunaDNA / LunaPBC: data contribution in exchange for equity (SEC Reg A)
- Agency/date: SEC Regulation A Tier 2 offering, qualified December 3, 2018. Later circulars 2021 and 2022.
- URL: https://www.sec.gov/Archives/edgar/data/1741687/000119312522253279/d375583d253g2.htm ; https://medcitynews.com/2019/07/lunapbc-is-trading-company-shares-for-member-health-data/
- What it says:
  - Members receive LLC shares (deemed about $0.07/share), not cash, for contributing genomic, medical, device and survey data. Examples: 4 shares for a prescription report; 10 shares for 20 days of certified-device data; 300 shares for a whole genome (2019).
  - Members can delete their data at any time.
  - The SEC treated these shares as securities, which required a registered/qualified offering.
- Resemblance: high. An individual contributes combined health data and receives value per data type.
- Implication: this is the most important regulatory signal for us. If compensation is a share of profits, tokens with expected appreciation, or a pooled "data dividend", the SEC may treat it as a security. Plain per-round cash or stablecoin payment for completed participation is the low-risk structure. Avoid profit-share or token-appreciation framing; on XRPL, pay in stable value per completed round. No FTC or SEC enforcement against Luna was found.
- KR: 데이터 기여 대가로 지분을 준 LunaDNA는 SEC 증권 공모 절차를 거쳤음. 수익 배분·토큰 가치 상승형 보상은 증권 이슈. 회차별 고정 보상이 안전.

## 6. 23andMe bankruptcy sale and research data (2025)
- Agency/date: US Bankruptcy Court (E.D. Mo.). Sale approved mid-2025. More than 30 state AGs objected. Minnesota AG alert September 2025.
- URL: https://www.mobihealthnews.com/news/judge-approves-23andme-sale-amid-privacy-dispute ; https://alaskabeacon.com/2025/07/09/under-bankruptcy-settlement-alaskans-can-request-23andme-immediately-delete-their-dna-data/ ; https://ag.state.mn.us/Office/Communications/2025/09/10_23andMe.asp
- What it says:
  - The sale went to TTAM Research Institute (later renamed 23andMe Research Institute), a nonprofit led by Anne Wojcicki, for $305M.
  - Objections were overruled. California argued the sale violated its Genetic Information Privacy Act's opt-in consent rule for selling genetic data.
  - TTAM committed to keep existing policies on deletion and research opt-out, and to verifiable deletion that states can check.
  - Search results did not confirm the earlier Regeneron bid (UNVERIFIED).
- Resemblance: medium-high. A research-consented health data pool changes hands, and consent and deletion promises have to survive the transfer.
- Implication: promises on deletion and research consent must bind successors. Add a clause covering change of control or insolvency. Make deletion verifiable, for example with a deletion receipt logged on XRPL. Do not keep a central pool when the agent-held model can avoid one.
- KR: 23andMe 파산 매각 시 주(州) 검찰총장들이 동의·삭제 약속 승계를 요구. 인수·파산 시에도 삭제·동의 약속이 유지되도록 설계.

## 7. Apple Research app / Apple Heart and Movement Study (2019 to present)
- Sponsor: Apple with Brigham and Women's Hospital and the American Heart Association. IRB-approved. Launched November 2019.
- URL: https://heart.org/-/media/Files/Get-Involved/Apple-Study/Apple-Heart-and-Movement-Study-FAQs.pdf ; https://techcrunch.com/2019/11/14/apple-research-app-arrives-on-iphone-and-apple-watch-with-three-opt-in-health-studies/
- What it says:
  - Participants consent in the app.
  - Withdrawal is possible at any time and stops further data collection.
  - Consent is renewed every two years, and the study is expected to run at least 5 years.
  - Results go to ClinicalTrials.gov without direct identifiers.
  - What happens to data already shared on withdrawal: not found (UNVERIFIED).
  - No participant payment was found.
- Resemblance: high. App-mediated consent for wearable data with in-app withdrawal.
- Implication: in-app e-consent run by a study team under an IRB is a precedent regulators accept. The periodic re-consent (every 2 years) supports our per-use or per-round consent. Each receiving institution still needs its own IRB approval and consent document. Our app delivers that consent but does not replace it.
- KR: 앱 내 전자동의·언제든 철회·2년마다 재동의. 회차별 동의 설계의 근거 사례이나 연구기관 IRB 승인은 별도로 필요.

## 8. FTC v. Flo Health (2021)
- Agency/date: FTC. Proposed January 2021, finalized June 22, 2021.
- URL: https://www.ftc.gov/news-events/news/press-releases/2021/06/ftc-finalizes-order-flo-health-fertility-tracking-app-shared-sensitive-health-data-facebook-google
- What it decided:
  - Flo had promised privacy but shared fertility and health data with Facebook, Google and analytics firms.
  - The order requires affirmative express consent before sharing health data. Per a law-firm summary, the consent must name the categories of data, the recipients and the purpose, and must be separate from the privacy policy or terms.
  - Flo had to notify users and instruct recipients to destroy the data, and obtain an independent privacy review.
  - It is barred from misrepresenting its practices or the control users have.
  - No money penalty.
- Resemblance: medium. A health app sharing with third parties; our recipients are research institutions, not ad platforms.
- Implication: the per-use consent screen should name the data categories, the named institution, the purpose and the retention period, separate from the terms of service. Build a "notify recipient to destroy" workflow for deletion requests.
- KR: 건강정보 제3자 제공 전 '적극적 명시 동의'(데이터 범주·수령자·목적 명시) 필요, 수령자에게 삭제 지시 의무.

## 9. FTC v. GoodRx (2023): first HBNR enforcement
- Agency/date: FTC/DOJ. Announced February 1, 2023. Stipulated order reported entered February 17, 2023 (sources differ on timing).
- URL: https://www.hunton.com/privacy-and-information-security-law/goodrx-to-pay-1-5-million-in-first-ever-ftc-health-breach-notification-rule-enforcement-action ; https://www.davispolk.com/insights/client-update/ftc-brings-first-enforcement-action-under-health-breach-notification-rule
- What it decided:
  - GoodRx shared health data with Facebook, Google and Criteo through pixels and SDKs, and did not notify anyone.
  - $1.5M civil penalty.
  - Ban on sharing health data for advertising.
  - Affirmative express consent required for any other third-party sharing.
  - Recipients must be told to delete the data.
- Resemblance: medium. The relevant risk for us is embedded analytics or SDKs in our app leaking data.
- Implication: no third-party ad or analytics SDKs on health screens. An "unauthorized disclosure" under the HBNR can be a tracking pixel.
- KR: 첫 HBNR 집행. 광고용 공유 금지·$1.5M. 앱에 광고/분석 SDK를 넣으면 그 자체가 '침해'가 될 수 있음.

## 10. FTC v. BetterHelp (2023)
- Agency/date: FTC. Proposed March 2, 2023. $7.8M consumer refunds, with refund distribution reported in 2024.
- URL: https://www.hunton.com/privacy-and-cybersecurity-law-blog/ftc-announces-proposed-order-against-betterhelp-for-disclosing-sensitive-mental-health-information-to-third-parties-for-targeted-advertising-purposes
- What it decided:
  - BetterHelp shared emails, IPs and intake answers (including hashed emails) with Facebook and Snapchat after promising privacy.
  - It falsely denied the sharing in 2020.
  - Ban on sharing health data for advertising.
  - Affirmative express consent before disclosure to third parties for any purpose.
  - Limits on retaining data.
- Resemblance: medium. Survey or intake answers are health data even when they look like "just questionnaire" data.
- Implication: our survey responses are health data. Do not share hashed identifiers on the theory that hashing makes them anonymous (see item 13). Public statements about our practices must match reality.
- KR: 설문(인테이크) 응답도 건강정보. 해시 이메일 공유도 문제됨, $7.8M 환급.

## 11. FTC v. Easy Healthcare (Premom) (2023): cross-border angle
- Agency/date: FTC/DOJ plus DC, Connecticut and Oregon. Proposed May 2023.
- URL: https://www.ftc.gov/news-events/news/press-releases/2023/05/ovulation-tracking-app-premom-will-be-barred-sharing-health-data-advertising-under-proposed-ftc
- What it decided:
  - Premom shared health data and device identifiers with AppsFlyer, Google and two China-based firms, without adequate encryption.
  - Violations of the HBNR and of Section 5 deception.
  - Ban on sharing for advertising, consent required for other sharing, and third parties told to delete.
  - $100k FTC civil penalty plus $100k to the states.
- Resemblance: medium-high on the cross-border element. Health data went to foreign recipients that users had not been told about.
- Implication: disclose every foreign recipient (Korea and Mongolia institutions) by name and country in the per-use consent, and encrypt in transit. The FTC treats undisclosed overseas transfer as an aggravating fact.
- KR: 중국 업체로의 미고지 건강정보 전송이 쟁점. 한국·몽골 기관 이전 시 국가·기관명을 동의 화면에 명시하고 암호화.

## 12. FTC v. 1Health.io / Vitagene (2023)
- Agency/date: FTC. Complaint June 2023, finalized September 2023.
- URL: https://ftc.gov/news-events/news/press-releases/2023/09/ftc-finalizes-order-1healthio-over-charges-it-failed-protect-privacy-security-dna-data-unfairly
- What it decided:
  - The company broke promises to destroy DNA samples and delete data on request. Its labs had no contractual destruction duty, and its weak data inventory meant it could not honour deletions.
  - Health and genetic data sat in public buckets.
  - In 2020 it changed its privacy policy retroactively to widen sharing without notice or consent, which the FTC called unfair.
  - $75k for refunds. Labs must destroy samples held more than 180 days.
  - Affirmative express consent required before third-party disclosure.
- Resemblance: high on deletion and policy-change mechanics.
- Implication:
  - Deletion promises need (a) a data inventory mapping every copy, (b) contracts obliging research recipients to delete or return data, and (c) evidence of deletion.
  - Never apply a new sharing policy to data contributed under an old consent. Re-consent per use, which our design already does.
- KR: 삭제 약속 불이행·소급적 개인정보처리방침 변경이 '불공정'. 수령 기관 계약에 삭제 의무 넣고 데이터 인벤토리 유지.

## 13. FTC v. Cerebral and FTC v. Monument (April 2024), plus FTC "hashing is not anonymous" blog (July 2024)
- Agency/date: FTC/DOJ, April 2024. FTC Technology Blog, July 2024.
- URL: https://www.ftc.gov/node/85135 ; https://themarkup.org/pixel-hunt/2024/04/22/cerebral-to-pay-7-million-fine-and-limit-health-data-use-for-ads-under-federal-order ; https://www.loeb.com/en/insights/passle/2024/07/reminder-from-the-ftc-hashing-doesnt-make-data-anonymous
- What it decided:
  - Cerebral (telehealth, mental health): about $7M package. Sources split it differently: about $5.1M refunds plus a $10M penalty suspended after $2M. Ban on using health data for most advertising, and simpler cancellation.
  - Monument (alcohol-use-disorder treatment): shared treatment data via trackers while implying protection, including HIPAA-style claims. Barred from sharing health data for advertising.
  - Hashing blog: hashed IDs are still identifiers. Data is "anonymous" only if it can never be linked back to a person. Cited BetterHelp, Premom and InMarket.
  - I did not confirm whether the court entered the Cerebral and Monument orders (UNVERIFIED).
- Resemblance: high for our pseudonymous study IDs.
- Implication: describe our study IDs as "pseudonymous/coded", never "anonymous" or "de-identified", unless HIPAA de-identification (Safe Harbor or Expert Determination) actually applies. Do not imply HIPAA protection if we are not a CE or BA. Make withdrawal and cancellation as easy as sign-up.
- KR: 해시·가명 ID는 '익명'이 아님. '익명' 표현 금지, HIPAA 보호 암시 금지, 철회는 가입만큼 쉽게.

## 14. FDA (2018) and SACHRP (2019) payment guidance, with university IRB policies
- Agency/date:
  - FDA, "Payment and Reimbursement to Research Subjects", January 2018 (Information Sheet).
  - HHS SACHRP Attachment A, "Addressing Ethical Concerns Regarding Offers of Payment to Research Participants", September 30, 2019.
- URL: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/payment-and-reimbursement-research-subjects ; https://www.hhs.gov/ohrp/sachrp-committee/recommendations/attachment-a-september-30-2019/index.html
- FDA 2018:
  - Payment should accrue as the study progresses, not be held to the end.
  - "Payment of a small proportion as an incentive for completion of the study is acceptable, providing that such incentive is not coercive."
  - The IRB judges amount, method and timing.
  - Reimbursing travel is not an undue-influence concern.
  - Payment is not a research benefit.
- SACHRP 2019: concerns about undue influence can be managed without necessarily lowering or eliminating payments. IRBs weigh the factors.
- University IRB policies:

  | Institution | Position on completion bonus | Source |
  |---|---|---|
  | Syracuse SOP 037 | Repeats the FDA "small proportion" language | https://researchintegrity.syr.edu/wp-content/uploads/2018/02/SOP-037-Payments-to-Research-Participants-revision-6.2-FINAL.pdf |
  | UC Irvine | Same "small proportion" language; IRB decides | https://research.uci.edu/wp-content/uploads/21-Participant-Compensation.pdf |
  | Pitt | A completion share is acceptable if not so large it induces "withdrawal-averse behavior" | https://www.hrpo.pitt.edu/node/645 |
  | Duke | Completion bonus "ordinarily discouraged" | https://irb.duhs.duke.edu/sites/default/files/2024-02/compensation_payments_to_research_participants_1-29-2024.pdf |
  | UNMC | Does not allow completion bonuses; requires proration | https://guides.unmc.edu/books/hrpp-policies-and-procedures/page/38-research-subject-compensation-and-reimbursement/revisions/777 |
  | UVA | Requires proration | https://hrpp.research.virginia.edu/node/1836 |

- Numeric caps:
  - No university policy with a hard percentage cap was found in the search results.
  - One secondary source (casrai.org guide) says "up to about 25%" can be held as a completion bonus. That is a practitioner rule of thumb (UNVERIFIED as policy). Some IRBs use 10 to 20% in practice (UNVERIFIED).
- Resemblance: direct, because our design holds back part of each round's payment for a quality check.
- Implication:
  - A holdback tied to *completion* would be treated like a completion bonus and should stay a small share. 25% is the outer bound of common practice; 10 to 20% is safer.
  - A holdback tied to *quality*, meaning data integrity (not fabricated, device-verified), is not an FDA concept. IRBs may see it as withholding earned payment. Frame it as "base payment always paid for each round completed; small quality bonus on validation". Never claw back the base payment for withdrawal.
  - Prorate per round. That is our design already.
- KR: FDA·SACHRP는 분할(비례) 지급 권장, 완료 보너스는 '소액 비율'만 허용(대학 IRB 수치 상한 미확인, 실무상 ~25% 이하). 품질 보류분은 기본보상과 분리된 소액 보너스로 설계.

## 15. Washington My Health My Data Act: first private suit, Maxwell v. Amazon.com (2025)
- Court/date: US District Court for the Western District of Washington, No. 2:25-cv-261, filed February 10, 2025.
- URL: https://www.wilmerhale.com/en/insights/blogs/wilmerhale-privacy-and-cybersecurity-law/20250220-first-lawsuit-filed-under-washingtons-my-health-my-data-act
- What it alleges:
  - Amazon's ad SDK in third-party apps collected location and biometric data, which counts as consumer health data under the Act, without the Act's consent.
  - Amazon used and sold it.
  - Also claims under the Wiretap Act, the Computer Fraud and Abuse Act (CFAA) and the Washington Consumer Protection Act.
  - The MHMDA gives a private right of action through the Washington Consumer Protection Act.
  - No ruling or settlement was found (status UNVERIFIED). I did not find any enforcement action by the Washington AG.
- Resemblance: medium. The MHMDA requires separate consent for collection and for sharing, and a signed "valid authorization" to *sell* consumer health data.
- Implication: if any Washington resident uses the app, paying users while institutions pay us for their data could be framed as a "sale". That would need the MHMDA's signed authorization, which expires after one year and must name the buyer. Per-use, named-recipient consent maps well onto it. Keep the consent record. (MHMDA authorization details are from prior knowledge: UNVERIFIED this session.)
- KR: 워싱턴주 MHMDA 첫 집단소송(아마존). 기관이 대가를 지급하는 구조는 '판매'로 볼 여지, 수령자 명시 서면 승인 필요.

---

## Not found or not verified this session
- Verily Project Baseline, PatientsLikeMe, Ciitizen/Invitae, Hu-manity.org: no searches were completed for these, and no regulator actions are known (UNVERIFIED).
- HHS ONC "Health app use scenarios & HIPAA" (2016): not re-verified.
- NIH Genomic Data Sharing policy withdrawal provisions: not searched.
- Cross-border transfers (prior knowledge, UNVERIFIED): the DOJ Bulk Sensitive Data Rule (28 CFR Part 202, effective April 2025) restricts US-person health and genomic data going to "countries of concern" (China, Russia, Iran, North Korea, Cuba, Venezuela). Korea and Mongolia are not on that list. Still screen recipient institutions for ownership or control by covered persons. The US has no general adequacy regime; the FTC focus is on disclosure (Premom).

## Bottom line for our design
1. Bringing hospital records in through the right of access is endorsed by OCR (item 1). We are then governed by the FTC and states, not HIPAA, and the HBNR almost certainly applies (item 3).
2. Per-use consent must be affirmative and express: data categories, named institution and country, purpose, retention, all separate from the terms of service (items 8 to 12).
3. Never call study IDs "anonymous" (item 13). Use no ad or analytics SDKs (items 9 to 11).
4. Withdrawal stops future use. Already-used data may be retained, and this must be stated up front (items 2 and 4). Deletion must reach recipients by contract and be provable (items 6 and 12).
5. Payment: prorate per round. Keep any held-back or quality amount small (about 10 to 20%, with 25% as the outer bound) and never forfeit it on withdrawal (item 14). Avoid profit-share or appreciating-token compensation because of SEC securities risk (item 5). The All of Us $25 is the public benchmark (item 4).
