"""DB 모델링 내용 (요구사항 정의서 v1.11, 화면설계서 v1.5 기준).

build_db_doc.py(발표 자료)와 erd.py(E-R 다이어그램)가 이 파일을 읽는다.
테이블을 고치면 두 스크립트를 다시 실행한다.
"""

TITLE = "물어봐 캠퍼스 DB 모델링"
VERSION = "1.0"
DATE = "2026-10-12"
TEAM = "캡스톤디자인 1조 · 22026018 송승현 · 22126008 이승우"
BASIS = "요구사항 정의서 v1.11 · 화면설계서 v1.5"

HISTORY = [
    ["v1.0", "2026-10-12", "요구사항 정의서 v1.11 기준 최초 작성 (서버 테이블 13개, E-R 다이어그램, RDM, 제약 조건)", "송승현"],
]

# 저장소 세 곳: 무엇을 어디에 두는지
STORES = [
    ("관계형 DB", "SQLite (개발·시연), 필요하면 PostgreSQL",
     ["수집 소스·원본 문서·청크 원문", "FAQ와 답변 대기 질문", "중간 관리자·인증 코드·세션", "질문 통계·수집 로그"],
     "답변 대기 → FAQ → 알림처럼 서로 이어지는 데이터를 정확하게 관리"),
    ("벡터 DB", "Chroma (FR-016)",
     ["청크 임베딩 (id = chunk_id)", "FAQ 임베딩 (id = faq-{faq_id})", "검색 필터용 메타데이터 (카테고리·캠퍼스·마감일)"],
     "의미가 비슷한 문장을 빠르게 찾기. 원문과 상태는 관계형 DB가 기준"),
    ("기기 저장", "Android Room · DataStore",
     ["대화 기록 (최대 50건, FR-008)", "관심 일정·알림 예약 (FR-021)", "캠퍼스·관심 분야·글씨 크기 설정 (FR-009)"],
     "개인 데이터는 서버로 보내지 않는다는 원칙(2.6)을 지키기"),
]

# 테이블 정의
# 필드: (이름, 타입, PK, FK 대상 또는 "", NULL 허용, 설명)
TABLES = [
    {
        "name": "source", "kor": "수집 소스", "group": "collect",
        "desc": "데이터 수집기가 가져오는 학교 홈페이지 메뉴·Open API 목록과 수집 주기",
        "fr": "FR-014, FR-022",
        "fields": [
            ("source_id", "INTEGER", True, "", False, "소스 고유 번호"),
            ("name", "VARCHAR(50)", False, "", False, "소스 이름 (예: 학사공지, 아산 주말 통학버스)"),
            ("category", "VARCHAR(20)", False, "", False, "학사정보·통학버스·동아리·교외활동·일반공지·캠퍼스시설"),
            ("campus", "VARCHAR(10)", False, "", True, "영동 / 아산 / 공통"),
            ("url", "VARCHAR(500)", False, "", False, "수집 주소 또는 API 주소"),
            ("menu_path", "VARCHAR(200)", False, "", True, "홈페이지 메뉴 경로 (예: 홈 > 커뮤니티 > 공지사항 > 학사공지)"),
            ("interval_min", "INTEGER", False, "", False, "수집 주기(분): 공지·교외활동 180, 나머지 1440"),
            ("is_active", "BOOLEAN", False, "", False, "수집 사용 여부"),
            ("last_success_at", "DATETIME", False, "", True, "마지막으로 수집에 성공한 일시 (수집 현황 화면)"),
        ],
    },
    {
        "name": "document", "kor": "원본 문서", "group": "collect",
        "desc": "수집한 페이지·공지·첨부파일과 관리자가 올린 보충 문서의 원본 정보",
        "fr": "FR-014, FR-015, FR-024",
        "fields": [
            ("doc_id", "INTEGER", True, "", False, "문서 고유 번호"),
            ("source_id", "INTEGER", False, "source.source_id", True, "수집 소스 (보충 문서는 NULL)"),
            ("parent_doc_id", "INTEGER", False, "document.doc_id", True, "첨부파일이면 원래 공지"),
            ("uploader_id", "INTEGER", False, "manager.manager_id", True, "보충 문서를 올린 관리자"),
            ("doc_type", "VARCHAR(10)", False, "", False, "페이지 / 공지 / 첨부 / API / 보충"),
            ("title", "VARCHAR(300)", False, "", False, "문서 제목"),
            ("url", "VARCHAR(500)", False, "", True, "원문 주소 (보충 문서는 NULL)"),
            ("provider", "VARCHAR(50)", False, "", True, "제공처 (보충 문서, 예: 학과 사무실)"),
            ("posted_at", "DATETIME", False, "", True, "게시일"),
            ("content_hash", "CHAR(64)", False, "", False, "본문 해시. 다시 수집했을 때 바뀐 문서만 찾기"),
            ("collected_at", "DATETIME", False, "", False, "수집 또는 업로드 일시"),
            ("is_deleted", "BOOLEAN", False, "", False, "원문에서 삭제됨 (청크도 함께 삭제)"),
        ],
    },
    {
        "name": "chunk", "kor": "청크", "group": "collect",
        "desc": "문서를 300~800토큰으로 나눈 조각. 벡터 DB에는 같은 chunk_id로 임베딩을 저장",
        "fr": "FR-015, FR-016, FR-020",
        "fields": [
            ("chunk_id", "VARCHAR(64)", True, "", False, "청크 ID (벡터 DB와 같은 키)"),
            ("doc_id", "INTEGER", False, "document.doc_id", False, "원본 문서"),
            ("category", "VARCHAR(20)", False, "", False, "카테고리 (검색 필터)"),
            ("campus", "VARCHAR(10)", False, "", True, "캠퍼스 (검색 필터)"),
            ("title", "VARCHAR(300)", False, "", False, "문서 제목 (청크 머리말)"),
            ("content", "TEXT", False, "", False, "청크 본문"),
            ("source_url", "VARCHAR(500)", False, "", True, "원문 보기 주소 (FR-007)"),
            ("menu_path", "VARCHAR(200)", False, "", True, "홈페이지 메뉴 경로 (FR-022)"),
            ("posted_at", "DATETIME", False, "", True, "게시일 (최신 게시물 우선)"),
            ("deadline", "DATETIME", False, "", True, "마감일. 추출이 불확실하면 NULL (FR-020)"),
            ("collected_at", "DATETIME", False, "", False, "수집 일시 (답변에 표시)"),
            ("indexed_at", "DATETIME", False, "", True, "벡터 DB에 반영한 일시"),
        ],
    },
    {
        "name": "collect_log", "kor": "수집 로그", "group": "collect",
        "desc": "소스별 수집 실행 결과. 실패하면 직전 데이터를 유지하고 여기에 오류를 남김",
        "fr": "FR-014, AVL-003",
        "fields": [
            ("log_id", "INTEGER", True, "", False, "로그 고유 번호"),
            ("source_id", "INTEGER", False, "source.source_id", False, "수집 소스"),
            ("started_at", "DATETIME", False, "", False, "시작 일시"),
            ("finished_at", "DATETIME", False, "", True, "종료 일시"),
            ("status", "VARCHAR(10)", False, "", False, "성공 / 실패"),
            ("doc_count", "INTEGER", False, "", False, "새로 받거나 바뀐 문서 수"),
            ("error_message", "TEXT", False, "", True, "실패 원인"),
        ],
    },
    {
        "name": "manager", "kor": "중간 관리자·관리자", "group": "admin",
        "desc": "답변·운영 관리 웹에 로그인할 수 있는 이메일. 관리자가 중간 관리자(학과 조교)를 등록·삭제",
        "fr": "FR-032, FR-033",
        "fields": [
            ("manager_id", "INTEGER", True, "", False, "고유 번호"),
            ("email", "VARCHAR(100)", False, "", False, "업무용 이메일 (UNIQUE)"),
            ("name", "VARCHAR(30)", False, "", True, "이름 (선택)"),
            ("affiliation", "VARCHAR(50)", False, "", True, "소속 (선택, 예: AI소프트웨어학과)"),
            ("role", "VARCHAR(10)", False, "", False, "관리자 / 중간 관리자"),
            ("is_fixed", "BOOLEAN", False, "", False, "서버 설정에 정한 관리자. 페이지에서 삭제 불가"),
            ("created_by", "INTEGER", False, "manager.manager_id", True, "등록한 관리자"),
            ("created_at", "DATETIME", False, "", False, "등록일"),
            ("last_login_at", "DATETIME", False, "", True, "마지막 로그인 일시"),
        ],
    },
    {
        "name": "auth_code", "kor": "인증 코드", "group": "admin",
        "desc": "이메일로 보낸 6자리 로그인 코드. 원문은 저장하지 않고 해시만 보관",
        "fr": "FR-033, PER-011",
        "fields": [
            ("code_id", "INTEGER", True, "", False, "고유 번호"),
            ("manager_id", "INTEGER", False, "manager.manager_id", False, "코드를 받은 이메일"),
            ("code_hash", "CHAR(64)", False, "", False, "6자리 코드의 해시"),
            ("sent_at", "DATETIME", False, "", False, "발송 일시 (같은 이메일 1분에 1회)"),
            ("expires_at", "DATETIME", False, "", False, "만료 일시 (발송 후 10분)"),
            ("fail_count", "INTEGER", False, "", False, "틀린 횟수 (5회면 10분 동안 로그인 제한)"),
            ("used_at", "DATETIME", False, "", True, "사용 일시 (한 번만 사용)"),
        ],
    },
    {
        "name": "login_session", "kor": "로그인 세션", "group": "admin",
        "desc": "로그인 상태. 12시간 유지하고, 이메일을 삭제하면 바로 끝남",
        "fr": "FR-032, FR-033",
        "fields": [
            ("session_id", "CHAR(64)", True, "", False, "세션 토큰의 해시"),
            ("manager_id", "INTEGER", False, "manager.manager_id", False, "로그인한 사람"),
            ("created_at", "DATETIME", False, "", False, "로그인 일시"),
            ("expires_at", "DATETIME", False, "", False, "만료 일시 (로그인 후 12시간)"),
        ],
    },
    {
        "name": "pending_question", "kor": "답변 대기 질문", "group": "answer",
        "desc": "근거를 못 찾아 자동 등록된 질문. 비슷한 질문은 한 행에 묶음",
        "fr": "FR-025, FR-028, FR-029, AVL-008",
        "fields": [
            ("pending_id", "INTEGER", True, "", False, "고유 번호"),
            ("question", "VARCHAR(200)", False, "", False, "대표 질문 (이름·학번·전화번호 형태는 가림)"),
            ("category", "VARCHAR(20)", False, "", True, "카테고리"),
            ("campus", "VARCHAR(10)", False, "", True, "캠퍼스"),
            ("question_count", "INTEGER", False, "", False, "같은 질문 수 (요약 메일·목록 정렬)"),
            ("status", "VARCHAR(10)", False, "", False, "대기 / 답변완료 / 담당아님 / 만료"),
            ("first_asked_at", "DATETIME", False, "", False, "처음 들어온 일시"),
            ("last_asked_at", "DATETIME", False, "", False, "마지막으로 들어온 일시"),
            ("expires_at", "DATETIME", False, "", False, "만료 일시 (처음 등록 후 30일)"),
            ("handled_by", "INTEGER", False, "manager.manager_id", True, "답변하거나 담당 아님으로 표시한 사람"),
            ("handled_at", "DATETIME", False, "", True, "처리 일시"),
        ],
    },
    {
        "name": "notify_token", "kor": "알림 대상", "group": "answer",
        "desc": "답변이 등록되면 알림을 보낼 익명 기기 토큰. 발송하거나 만료되면 행을 삭제",
        "fr": "FR-028, FR-030, 2.6",
        "fields": [
            ("token_id", "INTEGER", True, "", False, "고유 번호"),
            ("pending_id", "INTEGER", False, "pending_question.pending_id", False, "알림을 받을 질문"),
            ("fcm_token", "VARCHAR(255)", False, "", False, "익명 기기 토큰 (pending_id와 함께 UNIQUE)"),
            ("created_at", "DATETIME", False, "", False, "등록 일시"),
        ],
    },
    {
        "name": "faq", "kor": "FAQ", "group": "answer",
        "desc": "학과 조교 답변과 관리자가 등록한 자주 묻는 질문. 벡터 DB에도 색인해 답변 근거로 사용",
        "fr": "FR-006, FR-024, FR-029",
        "fields": [
            ("faq_id", "INTEGER", True, "", False, "고유 번호"),
            ("pending_id", "INTEGER", False, "pending_question.pending_id", True, "답변한 답변 대기 질문 (UNIQUE, 직접 등록하면 NULL)"),
            ("author_id", "INTEGER", False, "manager.manager_id", True, "작성자 (이메일이 삭제돼도 FAQ는 남음)"),
            ("ref_doc_id", "INTEGER", False, "document.doc_id", True, "근거 문서 (보충 문서, 선택)"),
            ("question", "VARCHAR(100)", False, "", False, "FAQ 질문 (100자 이내)"),
            ("answer", "TEXT", False, "", False, "답변"),
            ("category", "VARCHAR(20)", False, "", False, "카테고리"),
            ("campus", "VARCHAR(10)", False, "", True, "캠퍼스"),
            ("ask_count", "INTEGER", False, "", False, "이 FAQ로 답한 횟수 (추천 질문 순서)"),
            ("created_at", "DATETIME", False, "", False, "등록일 (출처 '학과 조교 답변 · 등록일')"),
            ("updated_at", "DATETIME", False, "", True, "수정일"),
            ("indexed_at", "DATETIME", False, "", True, "벡터 DB에 반영한 일시 (PER-010)"),
        ],
    },
    {
        "name": "synonym", "kor": "동의어", "group": "admin",
        "desc": "학교에서 쓰는 줄임말을 표준어로 바꿔 검색하기 위한 사전",
        "fr": "FR-002, FR-024",
        "fields": [
            ("synonym_id", "INTEGER", True, "", False, "고유 번호"),
            ("term", "VARCHAR(30)", False, "", False, "줄임말 (UNIQUE, 예: 수정)"),
            ("canonical", "VARCHAR(30)", False, "", False, "표준어 (예: 수강정정)"),
            ("created_by", "INTEGER", False, "manager.manager_id", True, "등록한 관리자"),
            ("created_at", "DATETIME", False, "", False, "등록일"),
        ],
    },
    {
        "name": "query_log", "kor": "질문 통계", "group": "stat",
        "desc": "일별 질문 수·평균 응답 시간 집계용. 기기·IP 등 사용자를 알 수 있는 정보는 저장하지 않음",
        "fr": "FR-008, FR-025, PER-001",
        "fields": [
            ("log_id", "INTEGER", True, "", False, "고유 번호"),
            ("question", "VARCHAR(200)", False, "", False, "질문 (이름·학번·전화번호 형태는 가림)"),
            ("category", "VARCHAR(20)", False, "", True, "선택 카테고리"),
            ("campus", "VARCHAR(10)", False, "", True, "설정 캠퍼스"),
            ("answer_type", "VARCHAR(10)", False, "", False, "문서 / FAQ / 되묻기 / 근거없음"),
            ("response_ms", "INTEGER", False, "", False, "처리 시간 (밀리초)"),
            ("created_at", "DATETIME", False, "", False, "질문 일시"),
        ],
    },
    {
        "name": "digest_log", "kor": "요약 메일 발송", "group": "stat",
        "desc": "답변 대기 요약 메일을 하루에 한 번만 보내기 위한 발송 기록",
        "fr": "FR-031, AVL-009",
        "fields": [
            ("digest_date", "DATE", True, "", False, "발송 날짜 (하루 1행)"),
            ("sent_at", "DATETIME", False, "", False, "실제 발송 일시 (서버가 꺼져 있었으면 켜진 뒤)"),
            ("pending_count", "INTEGER", False, "", False, "메일에 넣은 답변 대기 건수"),
            ("recipient_count", "INTEGER", False, "", False, "받은 중간 관리자 수"),
        ],
    },
]

GROUPS = {
    "collect": ("데이터 수집", "2A6F97"),
    "answer": ("답변 대기·FAQ", "C8553D"),
    "admin": ("관리자·인증", "1F3A5F"),
    "stat": ("통계·기록", "6C757D"),
}

# 관계: (관계명, 부모, 자식, 유형, 설명)
RELATIONS = [
    ("수집", "source", "document", "1 : N", "한 소스에서 여러 문서를 수집"),
    ("수집 기록", "source", "collect_log", "1 : N", "소스마다 수집할 때마다 로그 1건"),
    ("첨부", "document", "document", "1 : N", "공지 하나에 첨부파일 여러 개 (자기 참조)"),
    ("청킹", "document", "chunk", "1 : N", "문서 하나를 여러 청크로 나눔"),
    ("보충 문서 업로드", "manager", "document", "1 : N", "관리자가 보충 문서를 올림 (선택)"),
    ("근거 문서", "document", "faq", "1 : N", "FAQ 답변이 보충 문서를 근거로 씀 (선택)"),
    ("FAQ 작성", "manager", "faq", "1 : N", "학과 조교·관리자가 FAQ를 작성"),
    ("답변", "pending_question", "faq", "1 : 0..1", "답변 대기 질문 하나에 답변(FAQ)은 최대 1개"),
    ("알림 대상", "pending_question", "notify_token", "1 : N", "같은 질문을 한 여러 기기에 알림"),
    ("처리", "manager", "pending_question", "1 : N", "조교가 답변하거나 담당 아님으로 표시 (선택)"),
    ("인증 코드", "manager", "auth_code", "1 : N", "로그인할 때마다 코드 발송"),
    ("로그인", "manager", "login_session", "1 : N", "여러 기기에서 로그인 가능"),
    ("동의어 등록", "manager", "synonym", "1 : N", "관리자가 동의어를 등록"),
    ("중간 관리자 등록", "manager", "manager", "1 : N", "관리자가 중간 관리자 이메일을 등록 (자기 참조)"),
]

# 제약 조건과 삭제 규칙
CONSTRAINTS = [
    ("중간 관리자 삭제", "auth_code·login_session 함께 삭제 (CASCADE) → 로그인 즉시 종료. faq.author_id·pending_question.handled_by 등은 NULL로 (SET NULL) → 작성한 FAQ는 남음", "FR-032"),
    ("관리자 보호", "is_fixed = TRUE인 관리자는 삭제 불가. 중간 관리자는 manager를 등록·삭제할 수 없음 (서버에서 role 확인)", "FR-032"),
    ("같은 기기 같은 질문 1회", "notify_token (pending_id, fcm_token) UNIQUE. 알림 권한이 없으면 토큰 행 없이 question_count만 증가", "FR-028"),
    ("답변 1개", "faq.pending_id UNIQUE. 답변하면 pending_question.status = 답변완료, 알림 발송 후 notify_token 삭제", "FR-029, FR-030"),
    ("답변 대기 만료", "매일 expires_at 지난 '대기' 행을 '만료'로 바꾸고 notify_token 삭제", "AVL-008"),
    ("원문 삭제 반영", "document.is_deleted = TRUE가 되면 해당 chunk 행과 벡터 DB 임베딩을 삭제", "FR-016"),
    ("인증 코드", "만료(10분)·사용(used_at)·5회 실패한 코드는 로그인에 쓸 수 없음. 같은 이메일은 sent_at 기준 1분에 1회만 발송", "FR-033"),
    ("요약 메일 하루 1회", "digest_log.digest_date PK. 09:00 또는 서버가 켜진 직후 오늘 날짜 행이 없을 때만 발송", "FR-031, AVL-009"),
    ("개인정보", "학생 이름·학번·기기 ID·IP 컬럼 없음. 질문 문장은 저장 전에 이름·학번·전화번호 형태를 가림. fcm_token만 예외로 두고 발송·만료 후 삭제", "2.6"),
]

# 기기 저장 (서버 DB 아님)
DEVICE = [
    ("chat_message (Room)", "role(질문/답변), text, sources_json, created_at", "최근 50건만 보관, 설정에서 전체 삭제", "FR-008"),
    ("saved_deadline (Room)", "chunk_id, title, deadline, source_url, alarm_ids", "관심 일정과 알림 예약 정보, 마감일이 바뀌면 다시 예약", "FR-021"),
    ("settings (DataStore)", "campus, interests, font_size, deadline_alarm", "캠퍼스·관심 분야·글씨 크기·마감 알림 설정", "FR-009, FR-023"),
]
