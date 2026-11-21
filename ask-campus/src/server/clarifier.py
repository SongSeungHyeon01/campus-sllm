"""애매한 질문이면 바로 답하지 않고 되묻는다 (FR-027 되묻기).

11/20 사용자 결정: 구체적인 답을 주려면 질문이 분명해야 하므로, 애매한 질문에는 유도 질문과 선택지를 돌려준다.
앱·웹은 선택지를 버튼으로 보여주고, 고른 값을 이렇게 다시 보낸다.
- field == "department": 고른 학과를 요청의 department에 넣고 같은 질문을 다시 보낸다.
- field == "refine": 원래 질문 뒤에 고른 말을 붙여 다시 보낸다 ('장학금' + '신청 기간' → '장학금 신청 기간').

되묻는 경우 (규칙 기반. sLLM에 판단을 맡기면 매번 달라져서 쓰지 않았다)
1. 공모전 목록을 묻는데 학과를 모를 때 → 학과
2. 주제어 하나만 던진 질문 ('장학금', '등록금 알려줘') → 무엇이 궁금한지
3. 통학버스 시간을 묻는데 정류장이 없을 때 → 그 캠퍼스 시간표의 정류장
4. 뜻을 알 수 없을 만큼 짧은 질문 → 예시를 들어 다시 물어 달라고 함
"""
import re
from functools import lru_cache

from . import db, departments

# 주제어 하나만 물었을 때 고르게 할 세부 항목
TOPICS: dict[str, list[str]] = {
    "장학금": ["신청 기간", "신청 자격", "장학금 종류", "지급 금액"],
    "등록금": ["납부 기간", "분할 납부", "환불 기준"],
    "수강신청": ["신청 기간", "정정 기간", "신청 방법"],
    "수강정정": ["정정 기간", "정정 방법"],
    "휴학": ["신청 기간", "신청 방법", "최대 몇 학기"],
    "복학": ["신청 기간", "신청 방법"],
    "졸업": ["졸업 학점", "학위수여식 날짜", "졸업 유예"],
    "자퇴": ["신청 절차", "등록금 환불"],
    "전과": ["자격 요건", "신청 기간", "몇 번까지"],
    "계절학기": ["기간", "신청 방법", "수강료"],
    "기숙사": ["신청 기간", "비용", "문의처"],
    "생활관": ["신청 기간", "비용", "문의처"],
    "시험": ["중간고사 기간", "기말고사 기간"],
    "성적": ["성적 확인 기간", "성적 정정 기간", "성적장학금"],
    "학사일정": ["이번 달 일정", "기말고사", "다음 학기 개강"],
    "동아리": ["전체 동아리 목록", "운동 동아리", "공연·예술 동아리", "학술 동아리", "봉사 동아리", "종교 동아리"],
    "학식": ["오늘 메뉴", "이번 주 메뉴"],
    "증명서": ["재학증명서 발급", "졸업증명서 발급", "성적증명서 발급"],
    # 11/20 애매한 질문 50개 시험에서 엉뚱한 공지 하나로 답하던 말들
    "통학버스": ["시간표", "첫차·막차", "요금", "주말 시간표"],
    "취업": ["취업 공지", "채용 정보", "취업 지원 프로그램"],
    "채용": ["채용 공고", "교내 근로·조교 채용"],
    "봉사": ["봉사활동 모집", "봉사 동아리", "봉사 시간 인정"],
    "행사": ["이번 달 행사", "축제 일정", "비교과 프로그램"],
    "축제": ["축제 일정", "축제 장소"],
    "비교과": ["비교과 프로그램 신청", "비교과 페스티벌 일정"],
    "입학": ["신입생 모집 일정", "입학식 날짜"],
    "편입": ["편입 지원 자격", "편입생 학점 인정", "편입생 수강신청"],
    "주차": ["주차 등록 방법", "주차 요금"],
    "교수": ["교수님 연락처", "교수님 연구실 위치", "학과 교수 목록"],
    "해외연수": ["해외연수 장학생 모집", "신청 기간", "지원 자격"],
    "교환학생": ["교환학생 모집", "지원 자격"],
    "자격증": ["자격증 취득 지원", "자격증 특별학점"],
    "도서관": ["도서관 운영 시간", "열람실 이용", "도서 대출"],
    "학생증": ["학생증 발급", "학생증 재발급"],
    "근로장학": ["국가근로장학 신청 기간", "교내 근로장학 모집"],
    "공지": ["학사 공지", "장학 공지", "일반 공지"],
    "상담": ["학생 상담 신청", "진로·취업 상담"],
}
_ALIAS = {"장학": "장학금", "기숙사신청": "기숙사", "식단": "학식", "학식메뉴": "학식", "구내식당": "학식",
          "시험기간": "시험", "졸업요건": "졸업", "수강": "수강신청", "버스": "통학버스", "셔틀": "통학버스",
          "셔틀버스": "통학버스", "통학": "통학버스", "봉사활동": "봉사", "교수님": "교수", "알바": "근로장학",
          "근로": "근로장학", "인턴": "취업", "이벤트": "행사", "특강": "비교과"}
# 주제어 외에 붙어도 '주제만 물은 것'으로 보는 말
FILLER = set("알려줘 알려줘요 알려주세요 알려 궁금해 궁금해요 궁금합니다 뭐야 뭐예요 뭔가요 어때 어때요 정보 관련 좀 대해 대해서 "
             "안내 설명 해줘 있어 있어요 질문 문의 언제 어떻게 학교 우리 추천 추천해줘 소개 소개해줘 종류 목록 뭐있어 "
             "뭐가 뭐 무슨 좀알려줘".split())
_PARTICLE = re.compile(r"(은|는|이|가|을|를|에|에서|에대해|이요|요)$")
_BUS = ("버스", "통학", "셔틀")
_BUS_TIME = ("시간", "몇시", "몇 시", "첫차", "막차", "빠른", "다음", "언제", "운행")
_CONTEST = ("공모전", "경진대회", "콘테스트", "해커톤")
_CONTEST_LIST = ("요즘", "진행", "모집", "지금", "현재", "뭐있", "있어", "있나", "목록", "알려", "종류", "어떤", "마감", "임박", "빠른", "언제",
                 "정보", "찾", "추천", "보여")

# 순서·날짜를 묻는 말 ('마감 제일 빠른 거')은 특정 공모전 이름으로 보지 않는다
_ORDER = set("가장 제일 빠른 빠른순 날짜 마감 마감일 임박 곧 순서 먼저 언제 언제까지 기간 일정 최근 새로운 거 것".split())

# 무엇을 묻는지 정해 주는 말. 이 말이 있으면 주제어 하나라도 되묻지 않고 답한다.
# 11/21 페르소나 평가: '국가장학금신청언제까지에여'(띄어쓰기 없음), '전과몇번가능', '기숙사 문의'에 되물었다.
# '알려줘·뭐 있어·정보'처럼 무엇을 원하는지 모르는 말만 붙은 경우('장학금 알려줘')는 그대로 되묻는다
_ASK_WORDS = ("언제", "어디", "얼마", "몇", "누구", "어떻게", "방법", "기간", "마감", "가능", "문의", "연락처", "전화", "번호",
              "자격", "서류", "위치", "요금", "시작", "까지")


def _tokens(question: str) -> list[str]:
    out = []
    for w in re.findall(r"[가-힣A-Za-z0-9]+", question):
        if w in FILLER:
            continue
        stripped = _PARTICLE.sub("", w) if len(w) > 2 else w
        # 조사를 뗀 말이 아는 주제어일 때만 뗀다 ('장학금은' → '장학금'). '와이파이' → '와이파'처럼 잘리는 것을 막음
        base = stripped if (stripped in TOPICS or stripped in _ALIAS or stripped in FILLER) else w
        if base in FILLER:
            continue
        out.append(_ALIAS.get(base, base))
    return out


@lru_cache(maxsize=4)
def _stops(campus: str | None) -> tuple[str, ...]:
    """그 캠퍼스 통학버스 시간표에 나오는 정류장 이름 (자주 나오는 순)."""
    with db.connect() as con:
        rows = con.execute("SELECT content, campus FROM chunk WHERE category = '통학버스'").fetchall()
    count: dict[str, int] = {}
    for r in rows:
        if campus and r["campus"] not in (campus, "공통", None):
            continue
        for key, val in re.findall(r"([^/:\n]+?):\s*(\d{1,2}:\d{2})", r["content"]):
            tokens = [t for t in re.sub(r"\(.*?\)", " ", key).split() if t not in ("출발", "도착")]
            name = tokens[-1] if tokens else ""
            # 캠퍼스·학교는 정류장 선택지가 아님 (출발·도착 열 이름)
            if len(name) >= 2 and not name.endswith(("회차", "호차")) and "캠퍼스" not in name and name != "학교":
                count[name] = count.get(name, 0) + 1
    names = sorted(count, key=count.get, reverse=True)
    names = [n for n in names if not any(o != n and o.endswith(n) for o in names)]   # '터미널'은 '천안터미널'과 겹침
    return tuple(names[:8])


def check(question: str, campus: str | None, department: str | None) -> dict | None:
    """되물어야 하면 {"field", "question", "options"}, 아니면 None."""
    q = question.strip()
    compact = q.replace(" ", "")

    # 1) 공모전 목록 + 학과 모름. '공모전'만 보낸 것도 목록을 묻는 것으로 본다
    #    (11/20: '공모전' 한 단어에 지난 '다전공 수기 공모전 심사결과' 공지로 답했음)
    toks0 = _tokens(q)
    contest_only = any(w in compact for w in _CONTEST) and all(any(c in t for c in _CONTEST) or t in FILLER for t in toks0)
    # 11/21 페르소나 평가: '… 대학혁신지원사업 사례영상 경진대회는 언제까지 접수해요?'처럼 특정 공모전을 물으면
    # 학과를 되묻지 않는다 (공모전·목록 말이 아닌 내용어가 셋 이상이면 특정 공모전 질문으로 본다)
    content = [t for t in toks0 if len(t) >= 2 and t not in _ORDER and not any(c in t for c in _CONTEST)
               and not any(w in t for w in _CONTEST_LIST)]
    specific = len(content) >= 3
    if any(w in compact for w in _CONTEST) and not specific and (any(w in compact for w in _CONTEST_LIST) or contest_only):
        if not department and not departments.find_in(q):
            return {"field": "department",
                    "question": "어느 학과 학생인가요? 아래에서 고르거나, 목록에 없으면 학과 이름을 적어 주세요. 학과에 맞는 공모전을 먼저 보여 드릴게요.",
                    "options": departments.for_campus(campus) + [departments.MORE, departments.ALL],
                    # '전체 보기'를 누르면 화면이 이 목록(두 캠퍼스 학과 전체)으로 버튼을 바꾼다
                    "more": departments.for_campus(None) + [departments.ALL]}
        return None

    # 3) 통학버스 시간인데 정류장 없음
    # 11/20: '통학버스 시간표'도 정류장이 없으면 시간을 고를 수 없어 근거없음이 됐다 → 시간표도 정류장을 묻는다
    if any(w in compact for w in _BUS) and any(w.replace(" ", "") in compact for w in _BUS_TIME):
        stops = _stops(campus)
        names = {s for s in stops} | {s.removesuffix("역") for s in stops if len(s) > 2}
        if stops and not any(n in compact for n in names) and "터미널" not in compact:
            return {"field": "refine",
                    "question": "어느 정류장에서 타는지 알려 주세요. 그 정류장 기준으로 시간을 알려 드릴게요.",
                    "options": list(stops)}
        return None

    # 2) 단어 하나만 (주제 목록에 없는 말도). 11/20: '자격증', '비교과', '학생증'처럼 한 단어만 보내면
    #    가장 비슷한 공지 하나(지난해 공지·다른 학과 공지)로 답해서 엉뚱했다 → 무엇이 궁금한지 먼저 묻는다
    toks = _tokens(q)
    asks = any(w in compact for w in _ASK_WORDS)
    # '스마트팜공모전'처럼 공모전 말이 붙은 한 덩어리는 공모전 목록으로 (rag._contest_intent)
    contest_tok = len(toks) == 1 and any(w in toks[0] for w in _CONTEST)
    # '동아리 뭐 있어'는 목록을 원하는 것이 분명하다 → 되묻지 않고 분과별 목록으로 (rag._club_list)
    club_list = len(toks) == 1 and toks[0] == "동아리" and any(w in compact for w in ("뭐있", "목록", "종류", "몇"))
    if len(toks) == 1 and len(toks[0]) >= 2 and not asks and not contest_tok and not club_list:
        topic = toks[0]
        opts = TOPICS.get(topic) or ["신청 방법", "일정", "문의처"]
        return {"field": "refine",
                "question": f"{topic}에 대해 무엇이 궁금한가요? 아래에서 고르거나 더 자세히 적어 주세요.",
                "options": [o if topic in o or o.startswith(topic[:2]) or any(k in o for k in TOPICS) else f"{topic} {o}"
                            for o in opts]}

    # 4) 너무 짧아 뜻을 알 수 없음
    if len(compact) <= 2 or (len(toks) == 0 and len(compact) <= 6):
        return {"field": "refine",
                "question": "조금 더 자세히 물어봐 주세요. 예: '2학기 기말고사 언제야?', '두정역 통학버스 첫차 몇 시야?'",
                "options": []}
    return None
