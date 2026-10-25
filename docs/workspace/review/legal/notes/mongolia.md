# 몽골 법제: 개인 에이전트 기반 건강데이터 연구 기여 + XRPL 참여 대가 정산 (2026-10 기준, 해커톤 근거 요약, 법률 자문 아님)

> **조사 환경 한계 (반드시 읽을 것)**: 이 세션에서는 legalinfo.mn, frc.mn, cyrilla.org, gratanet.com, dlapiperdataprotection.com, wikisource.org 등 원문 페이지 직접 열람(fetch)이 네트워크 정책(프록시 403 / DNS 차단)으로 모두 실패함. 아래 내용은 **웹 검색 결과 스니펫·요약**에 근거하며, 조문 번호는 2차 자료(로펌 메모, 학술 논문, 컴플라이언스 사이트)에서 인용된 것임. 아래 "[미검증]" 표시가 붙은 조문 번호는 legalinfo.mn 몽골어 원문으로 교차확인 전까지 발표 자료에 확정 조문으로 쓰지 말 것. legalinfo.mn 영어본은 모두 **비공식 번역(Unofficial translation)**으로 표기되어 있음.
>
> 공식 원문 링크(열람 실패, 검색으로 존재만 확인):
> - Хүний хувийн мэдээлэл хамгаалах тухай хууль / Law on Personal Data Protection (PDPL): 몽골어 https://legalinfo.mn/mn/detail?lawId=16390288615991 , 영어 비공식 번역(2022.07.08 번역본) https://legalinfo.mn/en/edtl/16532053734461
> - Кибер аюулгүй байдлын тухай хууль / Law on Cyber Security: https://legalinfo.mn/en/edtl/16531350476261
> - Эрүүл мэндийн тухай хууль / Law on Health: 몽골어 https://legalinfo.mn/mn/detail/49 , 영어 https://legalinfo.mn/en/edtl/16959925340931
> - Эмнэлгийн тусламж, үйлчилгээний тухай хууль / Law on Medical Care and Services: https://legalinfo.mn/en/edtl/16959947100581
> - Эм, эмнэлгийн хэрэгслийн тухай хууль / Law on Medicines and Medical Devices: https://legalinfo.mn/en/edtl/16760184774901
> - Виртуал хөрөнгийн үйлчилгээ үзүүлэгчийн тухай хууль / Law on Virtual Asset Service Providers (VASP법): https://legalinfo.mn/mn/detail?lawId=16390242606091 , FRC 영문 PDF https://frc.mn/resource/frc/Document/2022/03/01/kl3q2fugnjqs9xqb/LAW%20ON%20VIRTUAL%20ASSET%20SERVICE%20PROVIDER.pdf

---

## Q1. 개인정보보호법 (Хүний хувийн мэдээлэл хамгаалах тухай хууль, PDPL; 2021.12.17 채택, 2022.05.01 시행)

### Takeaway
몽골 PDPL은 건강·유전·생체정보를 "민감정보(эмзэг мэдээлэл)"로 분류하고, 원칙적으로 **서면(종이 또는 전자) 동의** 또는 법률·조약상 근거가 있어야 수집·처리·이용할 수 있게 한다. 국외 이전도 동의 또는 법률/국제조약 근거가 필요하며 적정성 결정 제도는 없다. 과학·통계 목적 예외는 "개인을 식별할 수 없게 만든" 경우에 한정되는 것으로 보이므로, 가명 study ID만으로는 이 예외에 기대기 어렵고 **동의 중심 설계가 몽골에서도 기본값**이다. 특히 2차 자료상 하위 규정(민감정보 처리 규정)이 **서버의 몽골 국내 위치·국내에서만 접근** 요건을 두고 있다는 보고가 있어, 한국·미국으로의 데이터 흐름 설계에 가장 큰 제약 후보다.

### Cited Findings
**제정·시행·구법**
- 2021.12.17 국회 채택, 2022.05.01 전면 시행. 이전 1995년 개인비밀법(Law on Personal Secrecy)은 "동의" 요건을 명확히 두지 않았음 — [PwC Mongolia tax/legal alert 02/2022](https://www.pwc.com/mn/en/tax_alerts/pdf/tax_alert_en_02_2022.pdf); [PwC HTML판](https://www.pwc.com/mn/en/tax_alerts/tax_alert_02_2022.html)
- legalinfo.mn 영어본은 "(2022.07.08-ны өдрийн орчуулга) Unofficial translation"으로 표기 — [legalinfo.mn EN](https://legalinfo.mn/en/edtl/16532053734461)

**정의: 민감정보 (제4조 정의 조항) [하위 호 번호 미검증]**
- 민감정보 범주: 민족/인종 기원, 종교·신념, **건강**, 통신(서신), **유전정보·생체정보**, 전자서명 개인키, 범죄경력, 성적 지향·성별 정체성 등. 2차 자료 간 하위 호 번호가 4.1.11 vs 4.1.12로 **상충** — [DLA Piper Data Protection Laws of the World – Mongolia](https://www.dlapiperdataprotection.com/index.html?c=MN&t=law); [GRATA International 메모](https://gratanet.com/publications/legal-alert-new-law-on-protection-of-personal-data-in-mongolia); [GRATA 영문 번역 PDF](https://gratanet.com/laravel-filemanager/files/3/ENG-Law%20on%20Protection%20of%20Personal%20data.pdf)
- 생체정보 = 지문·홍채·얼굴·음성 등 신체 관련 물리적 데이터; 유전정보 = 개인의 신체 상태·건강·유전적 특성을 나타내는 고유 정보; 건강정보 = 신체·정신 건강 및 보건의료서비스 이용 여부 관련 정보 (정의가 각각 별도 호로 존재) — [DLA Piper](https://www.dlapiperdataprotection.com/index.html?c=MN&t=law); [GRATA](https://gratanet.com/publications/data-protection-and-employee-privacy-in-mongolia)
- 법은 개인정보를 성격별로 민감·기밀·생체·유전 정보 등으로 구분하고 이에 대해 강화된 요건을 둠; 별도 **「민감정보 처리 규정(Regulation on Processing Sensitive Data)」**이 민감·생체·유전 정보 처리 원칙과 기술적 보안조치·서버 요건을 규정 — [PwC Mongolia, Legal insights 2025.02.24](https://pwc.com/mn/en/services/legal_mn/legal-articles/legal_insights_feb_24_2025.html)

**민감정보 처리 원칙·제한**
- 민감정보의 수집·처리·이용은 정보주체의 서면 동의 또는 법이 정한 다른 법적 근거가 없으면 금지 — [PwC 2025 legal insights](https://pwc.com/mn/en/services/legal_mn/legal-articles/legal_insights_feb_24_2025.html); [Mondaq/GRATA](https://www.mondaq.com/data-protection/1181270/new-law-on-protection-of-personal-data-in-mongolia)
- **생체·유전정보는 일정 국가기관 외의 자의 수집·이용이 금지**된다고 2차 자료가 보고(사용자는 내부 노무규정에 따라 지문을 제외한 생체정보를 신원확인용으로 사용 가능) — [PwC 2025 legal insights](https://pwc.com/mn/en/services/legal_mn/legal-articles/legal_insights_feb_24_2025.html); [GRATA employee privacy](https://gratanet.com/publications/data-protection-and-employee-privacy-in-mongolia) [조문 번호·예외 범위 미검증 — 원문 확인 필수]
- 민감정보 처리 규정의 서버 요건: **서버는 몽골 영토 내에 위치해야 하고 몽골 국내에서만 접근 가능해야 함**; 전용 기술실, 정보교환 시스템 SSL 보호 등 — [PwC 2025 legal insights](https://pwc.com/mn/en/services/legal_mn/legal-articles/legal_insights_feb_24_2025.html) [규정 발령기관(디지털개발부 추정)·적용 대상 범위(공공/민간, 모든 민감정보 vs 생체·유전만) 미검증]

**동의의 형식·내용 (제8조로 인용되나 [미검증])**
- 정보주체는 정보관리자에게 **서면으로** 동의하며, 서면 동의는 **종이 또는 전자 형태**("Бичгээр өгөх зөвшөөрөл нь цаасан эсхүл цахим хэлбэртэй байна") — 법안 설명자료 및 검색 결과 요약 기준. 최종 법문 동일성은 원문 확인 필요 — [법안 설명자료(Slideshare)](https://www.slideshare.net/slideshow/ss-249659704/249659704); [legalinfo.mn MN](https://legalinfo.mn/mn/detail?lawId=16390288615991)
- 동의는 고지에 기반해야 하고 **철회권 고지**를 포함해야 한다고 2차 자료가 설명; 미성년자·행위무능력자는 법정대리인/후견인이 동의 — [Mondaq/GRATA](https://www.mondaq.com/data-protection/1181270/new-law-on-protection-of-personal-data-in-mongolia); [Pandectes](https://pandectes.io/blog/mongolias-data-privacy-law-key-features-and-implications-explained/)
- UNDP의 공공기관용 PDPL 가이드(몽골어, 2024.04)가 존재 — 동의 실무 해석 참고 가능 — [UNDP 가이드 PDF](https://www.undp.org/sites/g/files/zskgke326/files/2024-04/toriyn_bayguullaguudad_zoriulsan_garyn_avlaga.pdf)

**동의 철회**
- 정보주체는 서면 동의를 철회할 수 있다고 2차 자료가 보고 — [Pandectes](https://pandectes.io/blog/mongolias-data-privacy-law-key-features-and-implications-explained/); [ConsentStack](https://www.consentstack.io/regulations/mn-pdpl) [철회 조문 번호·철회 효과(기처리분 취급) 미검증]

**동의 없는 처리: 과학·통계 예외**
- 비동의 근거 중 하나로 "역사·과학·예술·문학 저작물, 공개데이터, 통계를 **개인을 식별할 수 없게 하는 방식**으로 작성"하는 경우가 열거됨 — [Lehman Law, Personal Data Protection in Mongolia](https://lehmanlaw.mn/blog/personal-data-protection-in-mongolia/); [Mondaq/GRATA](https://www.mondaq.com/data-protection/1181270/new-law-on-protection-of-personal-data-in-mongolia) [조문 번호 미검증]
- 별도의 "가명처리(pseudonymization)" 정의·특례(한국 PIPA 제28조의2 같은 가명정보 연구 특례)는 검색 자료에서 확인되지 않음.

**국외 이전**
- 법률 또는 몽골이 당사국인 국제조약에 달리 정함이 없는 한 **정보주체 동의 없는 국외 이전 금지**; 그룹사 내부 이전에도 예외 없음 — [Mondaq/GRATA](https://www.mondaq.com/data-protection/1181270/new-law-on-protection-of-personal-data-in-mongolia); [DLA Piper](https://www.dlapiperdataprotection.com/index.html?c=MN&t=law)
- UNSW 논문(Greenleaf 등)은 이 규정을 **제14조**로 인용하고, 몽골법에 적정성 결정 메커니즘이나 국외 이전에 대한 감독기관 역할이 없다고 평가 — [UNSW Law & Justice Research Series 2022/52 "Mongolia's Unique Data..."](https://www8.austlii.edu.au/au/journals/UNSWLRS/2022/52.pdf) [조문 번호 2차 인용, 미검증]
- 외국 개인·법인·국제기구로의 이전에 적용된다는 요약도 있음 — [Governance Atlas](https://atlas.ayoadeabel.tech/countries/mongolia)

**자동화 처리**
- 자동화된 의사결정에 관한 독립 조항은 검색 자료에서 확인 못 함 (Gaps 참조).

**감독기관**
- **몽골 국가인권위원회(Хүний эрхийн Үндэсний Комисс, NHRCM)**가 개인정보 보호 준수 감독·민원 처리 — [Montsame "Хүний хувийн мэдээллийг Хүний эрхийн Үндэсний Комисс хамгаална"](https://montsame.mn/mn/read/296754); [OUP IDPL 논문](https://academic.oup.com/idpl/article/15/1/67/8112931)
- 디지털개발(통신) 담당 부처가 기술·보안 측면을 담당한다는 요약 — [Governance Atlas](https://atlas.ayoadeabel.tech/countries/mongolia); [ksandk 요약은 감독기관 서술 불일치 있어 신뢰도 낮음](https://ksandk.com/privacy-review/map/mongolia/)
- 독립 전담 DPA가 없고, NHRCM은 검사형 규제기관보다 옴부즈만에 가깝다는 평가 — [OUP IDPL "Data privacy laws in Central Asia"](https://academic.oup.com/idpl/article/15/1/67/8112931)

**위반 제재 (Зөрчлийн тухай хууль / Law on Infringements; Эрүүгийн хууль / Criminal Code)**
- 위반법상 벌금 액수에 대해 2차 자료 **상충**: (a) 허용 목적 외 이용 시 개인 MNT 500,000 / 법인 MNT 5,000,000 — [Pandectes](https://pandectes.io/blog/mongolias-data-privacy-law-key-features-and-implications-explained/); (b) 형사책임 대상 아닌 불법 수집·처리·이전 시 개인 MNT 2,000,000 / 법인 MNT 20,000,000 — [Mondaq/GRATA](https://www.mondaq.com/data-protection/1181270/new-law-on-protection-of-personal-data-in-mongolia). (2022 개정 이후 액수 변동 가능, 원문 확인 필요)
- 유전정보 등 민감정보의 불법 수집·처리·이전 등 중대 위반은 형법상 책임 가능 — [PwC 2025 legal insights](https://pwc.com/mn/en/services/legal_mn/legal-articles/legal_insights_feb_24_2025.html)

**침해 통지**
- 관리자는 당국과 정보주체에게 통지해야 한다는 요약 존재, 그러나 **72시간 등 구체 기한은 확인되지 않음** — [ConsentStack](https://www.consentstack.io/regulations/mn-pdpl)

### Inferences
- 설계 적합성: "회차별·용도별 동의 + 전자 서명 동의"는 몽골 PDPL의 "서면(종이/전자) 동의" 요건과 정합적일 가능성이 높음. 단 동의 화면에 목적·항목·제공받는 자(기관명)·보유기간·**철회권**·**국외 이전 여부와 국가(한국·미국)**를 명시해야 안전.
- 과학·통계 예외는 "식별 불가" 산출물(통계 등)에 관한 것으로 보이며, 연구별 가명 study ID로 개인 단위 레코드를 기관에 넘기는 구조는 이 예외로 정당화하기 어렵다 → 몽골에서는 **동의를 1차 법적 근거**로 둘 것. 문서에서 "재식별 불가" 대신 "재식별 위험 감소"로 표현 유지.
- 국외 이전: 몽골 참여자 데이터를 한국·미국 연구기관이 복호화하는 구조는 국외 이전에 해당할 가능성이 높으므로 이전 국가·수령자를 동의 항목에 포함해야 함. 적정성 제도가 없으므로 동의가 사실상 유일한 실무 경로.
- **가장 큰 리스크**: (1) 민감정보 처리 규정의 "서버 몽골 국내 위치·국내 접근" 요건이 민간 처리자에도 적용된다면, UniQdata Core 서버를 몽골에 두는 것은 맞지만 한국·미국 기관의 접근 자체가 충돌할 수 있음. (2) 생체·유전정보 수집 주체 제한이 민간 연구 기여에도 적용되는지 불분명 → MVP에서는 **유전체·생체인식(얼굴·지문 등) 항목 제외**를 권고하는 것이 보수적. 웨어러블 심박·걸음수 등은 "건강정보"이지만 "생체정보(biometric) 정의"와 구분해 설명할 것(정의상 생체정보 = 신원 식별용 신체 특징).
- 개인 에이전트가 참여자 본인 기기에서 동작하고 본인이 직접 제공한다면 "정보주체 본인 제공" 성격이 강해지나, 플랫폼 운영자(UniQdata)가 처리·중계하는 순간 정보관리자/처리자 의무가 발생할 수 있음(관리자/처리자 정의 원문 확인 필요).

### Gaps
- 조문 번호 전반(정의 호수, 동의 조항 제8조 여부, 철회 조항, 과학·통계 예외 조항, 국외 이전 제14조 여부, 처리자 의무, 침해 통지 기한)은 원문 열람 실패로 **미검증**.
- 자동화된 처리/프로파일링 관련 조항 존재 여부 확인 못 함.
- "민감정보 처리 규정"의 정식 명칭·발령기관·발령일·민간 적용 범위 미확인.
- 위반법 벌금 액수 상충(위 참고), 2022년 이후 개정 여부 미확인.
- NHRCM의 PDPL 해석 지침·결정례 확인 못 함.

---

## Q2. 동반 2021년 법률: 공공정보(투명성)법, 사이버보안법

### Takeaway
사이버보안법(Кибер аюулгүй байдлын тухай хууль, 2021.12.17 채택)은 보건·에너지·결제 부문 등 **핵심정보인프라(CII)** 운영자에게 강화된 보안의무를 부과한다. 몽골 병원 파트너가 CII로 지정돼 있으면 연동(EMR 추출) 시 그 기관의 보안 요건을 충족해야 한다. 공공정보(투명성)법(Нийтийн мэдээллийн ил тод байдлын тухай хууль)의 관련 조문은 이번 조사에서 확보하지 못했다.

### Cited Findings
- 사이버보안법은 2021.12.17 채택; 에너지·보건·결제 등 부문의 핵심정보인프라 보유 기관을 대상으로 함 — [dig.watch Cybersecurity Law of Mongolia](https://dig.watch/resource/cyber-security-law-of-mongolia); [legalinfo.mn EN](https://legalinfo.mn/en/edtl/16531350476261)
- CII = 사이버보안 장애 시 해당 기관 운영 마비 및 몽골의 안보·사회·경제에 해를 끼칠 수 있는 조직; 정부가 CII 목록 관리(지정 근거로 제19조 인용), 2022년 정부결의로 목록 발령 — [NCSI Mongolia](https://ncsi.ega.ee/country/mn/?allData=1); [Oxford GCSCC Cybersecurity Capacity Review Mongolia (2025.02)](https://gcscc.ox.ac.uk/sites/default/files/gcscc/documents/media/mongolia_cmm.pdf) [제19조 미검증]
- CII 운영자: 2년마다 보안평가, 연 1회 정보보안 감사 등 강화 의무 — [Secure60/secopsolution 요약(상업 자료)](https://www.secure60.io/compliance/iso-27001-mongolia)

### Inferences
- 병원 파트너가 CII 지정 기관이면 데이터 추출 API/연계에 감사·보안평가 요건이 따라올 가능성. UniQdata Core 자체가 CII로 지정될 가능성은 낮으나 결제·보건 연계를 고려하면 확인 필요.

### Gaps
- 공공정보 투명성법의 관련 조문(공공기관 보유 개인정보 공개 제한 등) 미확보.
- 사이버보안법상 사고 신고 기한, 일반(비CII) 기관 의무 조문 미확보.

---

## Q3. 보건 법률: 보건법(Эрүүл мэндийн тухай хууль), 의료서비스법(Эмнэлгийн тусламж, үйлчилгээний тухай хууль), 연구윤리

### Takeaway
보건법은 2011년 개정판이 현행이며 2024.01.12 법률로도 개정되었고, 의료서비스법은 legalinfo.mn에 영어 비공식 번역(2023년 표기)이 있다. 환자의 의료비밀 보호·진료기록 열람권, 의료진 비밀유지 의무는 확인되나 정확한 조문 번호는 검증하지 못했다. 인간대상 연구윤리위원회는 의약품·의료기기법(임상시험, 제21.4항 윤리위원회)과 보건부 장관령 체계에 근거하는 것으로 보이나, 비임상 데이터 연구에 대한 IRB 의무 근거 조문은 확보하지 못했다.

### Cited Findings
- 보건법 legalinfo.mn 원문에 "2024 оны 01 дүгээр сарын 12-ны өдрийн хуулиар өөрчлөлт оруулсан"(2024.01.12 법률로 개정) 표기 — [legalinfo.mn 보건법](https://legalinfo.mn/mn/detail/49); 영어 [legalinfo.mn EN](https://legalinfo.mn/en/edtl/16959925340931)
- 보건법에는 생명공학·나노기술·혁신기술 기반 진단·치료 신제품·서비스의 연구·시험·검증·등록 절차를 보건 담당 장관과 과학 담당 장관이 공동 승인한다는 조항이 있음 — [legalinfo.mn EN 보건법](https://legalinfo.mn/en/edtl/16959925340931) [조문 번호 미확인]
- 의료서비스법 영어 비공식 번역은 적용범위를 "주민에게 제공되는 의료의 조직·관리·재정·감독"(1.1)으로 규정; 제7조(가정·솜 보건소 등록의 선택), 제38조(의료 소견서 발급) 확인 — [legalinfo.mn EN 의료서비스법](https://legalinfo.mn/en/edtl/16959947100581) [환자 기록 열람·비밀유지 조문 미확인]
- 환자의 진료 관련 신체·건강 비밀 및 사생활 비밀 보유 권리, 의료기관 전 직원의 직업상 비밀유지 의무, 진료기록(өвчний түүх)은 의료·법률상 비밀문서로 법이 허용하는 경우 외에는 동의 없이 열람·제공 금지라는 해설·법안 자료 — [의료전문가 법적지위법 초안(국회 lawforum)](https://lawforum.parliament.mn/draft/45/); [MongolMed](https://mongolmed.mn/article/3449) [2차/초안 자료]
- 공공병원의 진료기록 열람 신청 서비스 존재(본인 열람 실무) — [ssch.gov.mn "Өвчний түүх нээлгэх"](https://ssch.gov.mn/service/en?parent=4&current=42)
- 의약품·의료기기법: 임상시험 종료·조기중단 시 **제21.4항에 규정된 윤리위원회**에 통지 — [legalinfo.mn EN 의약품·의료기기법](https://legalinfo.mn/en/edtl/16760184774901); 2024.05 전면 개정 — [P4H Network](https://p4h.world/en/news/comprehensive-changes-to-mongolias-law-on-medicines-and-medical-devices-include-price-regulation-and-other-advances/)
- 보건 관련 법 개정 동향(공중보건법 제정 등) — [P4H 공중보건법](https://p4h.world/en/news/following-the-adoption-of-the-first-public-health-law-mongolia-kicked-off-the-year-of-public-health-promotion/)

### Inferences
- 병원 기록의 연구 기여 경로는 "환자 본인이 열람·사본 수령 → 개인 에이전트가 동의 범위 내 제공" 구조가 의료비밀 조항과 가장 충돌이 적음. 병원이 연구기관에 직접 제공하는 구조는 의료비밀·PDPL 양쪽 근거가 필요.
- 몽골 내 연구기관이 몽골 참여자 대상 연구를 하면 보건부 산하 의료윤리위원회(또는 기관 윤리위원회) 승인이 실무상 기대됨. 에이전트가 IRB 승인을 자체 판단·발행하지 않는다는 기존 원칙 유지.
- 몽골 국가 e-Health(전자의무기록) 플랫폼과의 직접 연동은 공공 시스템 접근 권한 문제로 MVP 범위 밖이 안전.

### Gaps
- 보건법·의료서비스법상 환자 기록 열람권·비밀유지·건강정보시스템 조문 번호 미검증.
- 보건부 의료윤리위원회 설치 근거(장관령 번호·연도), 비임상(데이터만 이용) 연구에 대한 윤리심의 의무 여부, 동의서 요건 미확보.
- 몽골 e-Health / 전자의무기록 법적 근거 미확보.

---

## Q4. 가상자산서비스제공자법 (Виртуал хөрөнгийн үйлчилгээ үзүүлэгчийн тухай хууль, 2021.12.17 채택)

### Takeaway
VASP법은 몽골에 등록된 영리법인이 몽골 내 또는 몽골에서 해외로 "타인을 위하여" 가상자산 교환·이전 등 제6.1조 열거 서비스를 제공할 때 **금융규제위원회(FRC/Санхүүгийн зохицуулах хороо) 등록**을 요구하고, VASP를 자금세탁방지법상 보고기관에 편입한다. 참여자 본인이 키를 보유하는 비수탁형 소프트웨어가 **연구기관의 자기 자금**으로 참여자에게 XRP를 지급하는 구조는 문언상 "타인을 위한 교환/이전" 서비스로 보기 어려울 가능성이 있으나, 플랫폼이 연구기관 자금을 대신 보관·송금하거나 법정화폐 환전을 제공하면 등록 대상이 될 위험이 크다.

### Cited Findings
- 채택 2021.12.17; 시행일은 자료 간 **상충**: 2022.02.24/25 — [Elliptic Mongolia guide](https://www.elliptic.co/country-guides/mongolia); [CryptoSlate](https://cryptoslate.com/crypto-laws/mongolia-law-on-virtual-asset-service-provider-2021/) vs 2022.02.14 공포·2022.03.01 시행 — [Mondaq "New Regulation On Virtual Asset Service"](https://webiis08.mondaq.com/fin-tech/1067722/new-regulation-on-virtual-asset-service); [Montsame](https://www.montsame.mn/jp/read/291643)
- 목적: 가상자산 서비스를 제공하는 법인의 등록, 활동 감독, 권리·의무 규정; 가상자산 = 결제·투자 목적으로 사용되는 가치의 무형 디지털 표현 — [Elliptic](https://www.elliptic.co/country-guides/mongolia/)
- 적용범위: 몽골에 등록된 영리법인과 그들이 몽골 내 및 몽골에서 해외로 제공하는 가상자산 서비스 — [Mondaq](https://webiis08.mondaq.com/fin-tech/1067722/new-regulation-on-virtual-asset-service); [CryptoSlate](https://cryptoslate.com/?p=550291)
- VASP = **제6.1조** 열거 활동을 영위하는 회사; 제6.1조는 타인을 위하여/타인의 지시로 수행하는 (1) 가상자산↔법정화폐 교환, (2) 가상자산 상호 교환, (3) 가상자산 이전(타인을 대신하여 가상자산 계정·주소 간 이동), 그 밖에 6.1.4, 6.1.5(공모·판매 관련) 등. 수탁(хадгалах)이 열거되는지는 스니펫상 미확인. 제6.2조: 공모·판매는 6.1.5 등록자로 한정 — [legalinfo.mn VASP법](https://legalinfo.mn/mn/detail?lawId=16390242606091); [gogo.mn 주요 조항 해설](https://gogo.mn/r/8x6k6); [FRC 법령·규정 모음(2023.03)](https://www.frc.mn/resource/frc/Document/2023/03/16/97x9rhalw2y1nbt3/%D0%92%D0%B8%D1%80%D1%82%D1%83%D0%B0%D0%BB%20%D1%85%D3%A9%D1%80%D3%A9%D0%BD%D0%B3%D0%B8%D0%B9%D0%BD%20%D2%AF%D0%B9%D0%BB%D1%87%D0%B8%D0%BB%D0%B3%D1%8D%D1%8D%20%D2%AF%D0%B7%D2%AF%D2%AF%D0%BB%D1%8D%D0%B3%D1%87%D0%B8%D0%B9%D0%BD%20%D1%85%D1%83%D1%83%D0%BB%D1%8C%20%D1%82%D0%BE%D0%B3%D1%82%D0%BE%D0%BE%D0%BC%D0%B6%D0%B8%D0%B9%D0%BD%20%D1%8D%D0%BC%D1%85%D1%8D%D1%82%D0%B3%D1%8D%D0%BB.pdf) [6.1.4~6.1.5 정확한 문언 미검증]
- FRC 미등록자는 가상자산 서비스 영위 불가; FRC는 법·FRC 요건 미충족 시 제한·정지·말소 가능(제11.1조) — [legalinfo.mn VASP법](https://legalinfo.mn/mn/detail?lawId=16390242606091); [Elliptic](https://www.elliptic.co/country-guides/mongolia)
- 자기자본 요건은 몽골은행(Mongolbank)과 FRC가 공동 승인 — [gogo.mn](https://gogo.mn/r/8x6k6)
- FRC는 2022.06.25부터 VASP 등록 개시, 기존 거래소는 2022.09.25까지 등록 — [Elliptic](https://www.elliptic.co/country-guides/mongolia/); FRC 등록·감독 절차(규정) 승인 — [GRATA "Relevant procedures for VASPs have been approved"](https://gratanet.com/publications/legal-alert-relevant-procedures-for-virtual-asset-service-providers-have-been-approved); FRC 규정안 [FRC VASP regulation 2022 PDF](https://frc.mn/resource/frc/Document/2022/02/28/ngo0fgyq1jfra7yb/VASP%20regulation_20220226_PDF%201-converted.pdf)
- FRC 2025 연차보고서: 몽골에서 **12개 법인**이 VASP로 영업 — [FRC Annual Report 2025](https://www.frc.mn/resources/Image/Document/202606/PWPKV/SZHoroo-2025-06-02edit-idml.pdf)
- legalinfo.mn에 VASP법 개정 이력 16건 표기(내용 미확인); 동시에 형법·위반법도 개정 — [legalinfo.mn](https://legalinfo.mn/mn/detail?lawId=16390242606091); [ucc.mn](https://ucc.mn/)
- AML/CFT: VASP는 자금세탁·테러자금조달방지법(Мөнгө угаах болон терроризмыг санхүүжүүлэхтэй тэмцэх тухай хууль)상 보고기관으로 편입; 2024.06 AML법 개정으로 "공공정보 인프라"를 통한 고객확인 허용; APG 2025 후속보고서(재평가 없음)가 R.15(가상자산) 관련 조치 언급 — [APG Mongolia FUR 2025](https://www.apgml.org/sites/default/files/documents//Mongolia_FUR_without_re-rating_2025.pdf); [Mondaq](https://webiis08.mondaq.com/fin-tech/1067722/new-regulation-on-virtual-asset-service)
- 트래블룰: VASP에 적용된다는 서술과 "형성 중/불명확"이라는 서술이 **상충** — [Elliptic](https://www.elliptic.co/country-guides/mongolia/); [KnowYourCountry](https://www.knowyourcountry.com/country-aml-intelligence/country/mongolia/)

### Inferences
- 비수탁형(참여자 본인 지갑, 연구기관이 자기 지갑에서 직접 Escrow/Payment 서명) 구조라면 UniQdata가 "타인을 위하여" 교환·이전을 수행하지 않으므로 제6.1조 서비스에 해당하지 않을 여지가 있음. 다만 (a) UniQdata가 연구기관 자금을 풀링·보관하거나 대리 서명, (b) MNT↔XRP 환전 제공, (c) MPT를 일반에 발행·판매(6.1.5 공모 해당 가능)하면 등록 리스크가 커짐. MPT를 "연구 라이선스 토큰"으로 쓰는 경우 투자 목적 판매로 비치지 않게 양도 제한·비매매 설계를 문서화할 것.
- 몽골 VASP법은 몽골 등록 법인 대상이므로, 해외 법인이 몽골 거주자에게 제공하는 경우의 적용은 문언상 불명확(원문 확인 필요).
- XRPL 원장 공개성 + 몽골 PDPL: 지급 주소와 연구 참여 사실이 연결되면 "건강 관련 연구 참여" 자체가 민감정보 추론 단서가 될 수 있으므로 메모 필드에 연구명·질환명 기재 금지.
- 해커톤 데모는 Testnet·실자금 없음 → 현 단계 등록 이슈 없음. 실서비스 전 몽골 현지 자문 + FRC 사전 문의 권고.

### Gaps
- 제6.1조 전체 문언(특히 수탁 포함 여부), 제4조 정의 문언 원문 미검증.
- 16건 개정의 내용과 2023~2026 개정 여부, FRC 트래블룰 규정(결의 번호·기준금액) 미확보.
- 비수탁형 소프트웨어에 대한 FRC 해석·유권해석 미발견.

---

## Q5. FRC 또는 개인정보 감독기관의 해석·지침

### Takeaway
FRC는 VASP 등록·감독 절차 규정을 승인·공개했고(2022), NHRCM 관련해서는 UNDP와 함께 공공기관용 PDPL 가이드가 2024년에 나왔다. 이번 시스템 같은 비수탁 지급이나 연구 목적 건강데이터 처리를 직접 다룬 공식 해석은 찾지 못했다.

### Cited Findings
- FRC VASP 등록·감독 절차 승인 — [GRATA legal alert](https://gratanet.com/publications/legal-alert-relevant-procedures-for-virtual-asset-service-providers-have-been-approved); [Mondaq](https://webiis05.mondaq.com/financial-services/1214916/legal-alert-relevant-procedures-for-virtual-asset-service-providers-have-been-approved)
- FRC "VASP 법령·규정 모음"(2023.03) — [FRC PDF](https://www.frc.mn/resource/frc/Document/2023/03/16/97x9rhalw2y1nbt3/%D0%92%D0%B8%D1%80%D1%82%D1%83%D0%B0%D0%BB%20%D1%85%D3%A9%D1%80%D3%A9%D0%BD%D0%B3%D0%B8%D0%B9%D0%BD%20%D2%AF%D0%B9%D0%BB%D1%87%D0%B8%D0%BB%D0%B3%D1%8D%D1%8D%20%D2%AF%D0%B7%D2%AF%D2%AF%D0%BB%D1%8D%D0%B3%D1%87%D0%B8%D0%B9%D0%BD%20%D1%85%D1%83%D1%83%D0%BB%D1%8C%20%D1%82%D0%BE%D0%B3%D1%82%D0%BE%D0%BE%D0%BC%D0%B6%D0%B8%D0%B9%D0%BD%20%D1%8D%D0%BC%D1%85%D1%8D%D1%82%D0%B3%D1%8D%D0%BB.pdf)
- 공공기관용 개인정보 보호 가이드(UNDP, 2024.04) — [UNDP PDF](https://www.undp.org/sites/g/files/zskgke326/files/2024-04/toriyn_bayguullaguudad_zoriulsan_garyn_avlaga.pdf)

### Inferences
- 공식 지침 공백이 크므로, 해커톤 자료에서는 "몽골법상 허용됨"이라는 단정 대신 "동의 기반 설계로 리스크 최소화, 실서비스 전 현지 확인"으로 표현.

### Gaps
- NHRCM의 PDPL 결정례·지침, FRC의 비수탁 지갑/소프트웨어 관련 해석 미발견.

---

## Q6. 암호자산으로 지급되는 참여 대가의 세무 (간략)

### Takeaway
가상자산 서비스가 부가가치세 면제라는 2차 자료가 있을 뿐, 개인이 받은 가상자산 참여 대가의 개인소득세 취급은 확인하지 못했다.

### Cited Findings
- 가상자산 서비스는 VAT 면제라는 서술 — [Mondaq "New Regulation On Virtual Asset Service"](https://www.mondaq.com/fin-tech/1067722/new-regulation-on-virtual-asset-service) [2차 자료, 현행 여부 미검증]

### Inferences
- 몽골 개인소득세법(Хувь хүний орлогын албан татварын тухай хууль, 2019 개정)상 용역 대가·기타 소득으로 과세될 가능성이 있으나 근거 미확보 → 참여자 안내문에 "세무 처리는 거주국 법에 따름" 문구와 지급 내역(원화/투그릭 환산가 포함) 제공 기능 권고.

### Gaps
- 가상자산 수령 시 소득 인식 시점·평가 방법, 원천징수 의무, 비거주 지급자(한국·미국 기관)의 원천징수 문제 모두 미확보.
