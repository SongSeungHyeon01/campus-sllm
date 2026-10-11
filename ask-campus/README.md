# 물어봐 캠퍼스 MVP 프로토타입

요구사항 정의서 v1.11 · API 명세서 v1.0 · DB 모델링 v1.0을 기준으로 만든 최소 기능 프로토타입입니다.

## 들어간 기능

| 기능 | 요구사항 | 구현 |
|---|---|---|
| 학교 홈페이지 공개 페이지 수집 | FR-014, 015 | 학사·일반·장학 공지(게시판마다 최근 20건), 학사일정, 통학버스(영동·아산, 주말·방학 포함), 동아리현황. 요청 간격 1초 |
| 임베딩·벡터 검색 | FR-002, 016 | KURE-v1 (fp16) + Chroma, 캠퍼스 필터 |
| sLLM 근거 기반 답변 | FR-003, 004 | Kanana 1.5 2.1B Instruct (GPU bf16), 출처·메뉴 경로·원문 링크, 현재 날짜·요일·시각 전달 |
| 통학버스 시간표 조회 | FR-010 | 질문에 정류장 이름이 있으면 코드가 계산해 답함: 지금 이후 가장 빠른 차·다음 차, 첫차, 막차, 전체 시간. 평일/주말 시간표는 질문 → 오늘 요일 순으로 고름 |
| 근거 없음 → 답변 대기 자동 등록 | FR-005, 028 | 기준값 미만이거나 sLLM이 "찾을 수 없습니다"라고 하면 등록, 비슷한 질문은 묶어 '같은 질문 수' 증가 |
| 조교 답변 웹 → FAQ 즉시 반영 | FR-024, 025, 029 | 답변 대기 목록, 답변 작성, 담당 아님, FAQ 목록. 등록 즉시 같은·비슷한 질문에 '학과 조교 답변 · 등록일'로 답함 |
| Android 채팅 앱 | SCR-001 | Kotlin, 질문·답변·출처·원문 보기, 캠퍼스 선택, 서버 주소 설정 |

## 빠진 것 (MVP 범위 밖)

- 이메일 인증 코드 로그인(FR-033), 중간 관리자 관리(FR-032), 요약 메일(FR-031): 발송 계정이 정해지면 붙입니다. 지금 관리 웹은 **임시 비밀번호 로그인**입니다.
- 조교 답변 익명 알림(FR-030, FCM), 되묻기(FR-027), 카테고리 칩·추천 질문(FR-006), 마감 일정(FR-020), 설정 화면(SCR-004), 첨부파일 본문 추출, 자동 재수집 스케줄러.
- 파인튜닝(FR-017): 원본 모델 + 프롬프트로 동작합니다.

## 폴더

```
ask-campus/
  src/ingest/   수집기 (fetch.py, html_utils.py, schema.py, sources.py, run.py)
  src/server/   서버 (config, db, index, llm, rag, app, build_index, templates/)
  scripts/      smoke_test.py(대표 질문), e2e_test.py(조교 답변 흐름 전체)
  data/         수집 결과·DB·벡터 인덱스·로그 (git에 올리지 않음)
android/        Android 앱 (Kotlin)
```

## 1. 서버 준비 (처음 한 번)

PowerShell 기준, `ask-campus` 폴더에서:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install torch --index-url https://download.pytorch.org/whl/cu128
.venv\Scripts\python -m pip install -r requirements.txt
```

- GPU: NVIDIA 8GB 이상 (팀 노트북 RTX 5060 Laptop 8GB에서 확인). 모델 내려받기 약 7GB (KURE-v1 약 2.3GB, Kanana 약 4.5GB, 처음 실행 때 자동).
- GPU가 없는 PC에서는 `$env:ASK_USE_LLM="0"`으로 sLLM 없이 근거 문장만 돌려주게 할 수 있습니다 (시험용).

## 2. 수집과 색인

```powershell
.venv\Scripts\python -m src.ingest.run --notice-pages 2   # 약 1~2분, data/chunks.jsonl
.venv\Scripts\python -m src.server.build_index           # data/askcampus.db, data/chroma
```

## 3. 서버 실행

```powershell
$env:ASK_ADMIN_PASSWORD = "관리웹비밀번호"     # 직접 정함. 없으면 관리 웹 로그인 불가
$env:ASK_SECRET = "아무 긴 무작위 문자열"         # 로그인 쿠키 서명용
.venv\Scripts\python -m uvicorn src.server.app:app --host 0.0.0.0 --port 8000
```

- 시작할 때 두 모델을 GPU에 올리고 시험 생성을 한 번 해서 약 30초~1분 걸립니다. `http://localhost:8000/api/v1/health`가 `model_ready: true`면 준비 완료.
- 관리 웹: `http://localhost:8000/admin`
- 비밀번호·키는 환경 변수로만 넣고 파일이나 GitHub에 남기지 않습니다 (2.6).

## 4. 시험

```powershell
.venv\Scripts\python scripts\smoke_test.py      # 대표 질문 11개: 답변 유형·출처·시간
.venv\Scripts\python scripts\e2e_test.py        # 조교 답변 흐름 9단계 (ASK_ADMIN_PASSWORD 필요)
.venv\Scripts\python scripts\time_test.py       # 시각을 바꿔 가며 통학버스 질문 10개 (서버를 끄고 실행, GPU 메모리)
```

- 2026-10-12 결과: e2e 9/9, time_test 10/10. 답이 있는 질문 1.2~3.6초, 시간표 조회 0.1초 이하, 자료에 없는 질문 4개 모두 근거 없음 + 답변 대기 등록.
- **e2e 시험은 시험용 FAQ("졸업작품 전시회…")를 DB에 남깁니다.** 시연 전에는 관리 웹에서 확인하거나 `data/askcampus.db`를 지우고 2번(색인)을 다시 하세요.

## 5. Android 앱

빌드 (JDK 17~21 필요. Android Studio 내장 JBR이 Java 25면 Gradle 8.7이 실행되지 않음):

```powershell
cd ..\android
$env:JAVA_HOME = "C:\Program Files\Java\jdk-21.0.12.1"
.\gradlew.bat assembleDebug        # app\build\outputs\apk\debug\app-debug.apk
```

- Android Studio로 `android` 폴더를 열어도 됩니다 (Settings → Gradle JDK를 17~21로).
- 처음 빌드할 때 `local.properties`가 없으면 `sdk.dir=C:/Users/<사용자>/AppData/Local/Android/Sdk`로 만듭니다 (슬래시 사용).

접속:

- **에뮬레이터:** 기본 서버 주소 `http://10.0.2.2:8000/`이 PC의 서버를 가리킵니다. 노트북 하나로 서버와 에뮬레이터를 같이 돌리면 GPU 메모리가 모자라므로 에뮬레이터는 `-gpu swiftshader_indirect`로 실행합니다.
- **실제 폰:** PC와 같은 Wi-Fi에 연결하고, 앱 오른쪽 위 메뉴 → '서버 주소'에 `http://<PC IP>:8000/`을 넣습니다. Windows 방화벽에서 8000번 포트를 허용해야 할 수 있습니다.
- 디버그 빌드 전용 자동 질문 (adb는 한글 입력이 안 되어 Base64로 보냄):
  `adb shell am start -n kr.ac.u1.askcampus/.MainActivity --es q64 <UTF-8 질문의 Base64>`

## 알려진 한계

- 통학버스: 방학 기간을 아직 몰라서 평일은 학기 중 시간표로 봅니다 (질문에 '방학'이 있으면 방학 시간표). 정류장 이름이 없는 질문("다음 버스 언제야?")은 sLLM이 표 전체로 답해 느리고 틀릴 수 있습니다 (되묻기 FR-027 미구현).
- 근거 기준값 0.60은 질문 10개로 정했습니다. 테스트 질문셋 80개(FR-018)로 다시 정해야 합니다.
- 수집한 공지는 게시판마다 최근 20건뿐이고 첨부파일 내용은 들어가지 않습니다.
- 개발 중 만난 오류와 해결 과정: `docs/오류보고서/INDEX.md`
