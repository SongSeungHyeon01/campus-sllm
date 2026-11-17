"""서버 설정. 값은 환경 변수로 바꿀 수 있다."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # ask-campus/
DATA = ROOT / "data"
DB_PATH = Path(os.getenv("ASK_DB", DATA / "askcampus.db"))
CHROMA_DIR = Path(os.getenv("ASK_CHROMA", DATA / "chroma"))
CHUNKS_JSONL = DATA / "chunks.jsonl"
CHUNKS_LOGIN_JSONL = DATA / "chunks_login.jsonl"    # 로그인 필요한 FAQ·Q&A (src/ingest/run_login.py)
CHUNKS_SITE_JSONL = DATA / "chunks_site.jsonl"      # 학교 사이트 전체 메뉴 + 학과·대학원 사이트 (src/ingest/run_site.py)

EMBED_MODEL = os.getenv("ASK_EMBED_MODEL", "nlpai-lab/KURE-v1")
# 11/17 13개 모델 비교로 A.X 4.0 Light 4bit 채택 (문서/보고서/개발문서/sLLM_모델비교.md). 7B라 bf16(약 15GB)은 8GB GPU에 안 들어감
LLM_MODEL = os.getenv("ASK_LLM_MODEL", "skt/A.X-4.0-Light")
EMBED_DEVICE = os.getenv("ASK_EMBED_DEVICE", "cuda")  # "cpu"면 KURE를 CPU에서 돌림
LLM_QUANT = os.getenv("ASK_LLM_QUANT", "4bit")      # "4bit" | "8bit" | ""(bf16, GPU 16GB 이상일 때)
LLM_ADAPTER = os.getenv("ASK_LLM_ADAPTER", "")      # LoRA 어댑터 경로나 Hugging Face ID (없으면 원본 모델)
USE_LLM = os.getenv("ASK_USE_LLM", "1") == "1"       # 0이면 sLLM 없이 근거 문장만 돌려줌 (GPU 없는 PC에서 시험용)

TOP_K = 5                 # 벡터 검색 개수 (FR-002)
CONTEXT_K = 3             # sLLM에 넘기는 근거 수, 출처 표시도 최대 3개 (FR-004)
# 이보다 낮으면 근거 없음 (FR-005). 11/18 108문항 시험으로 0.60 → 0.55: 정답 63→68/71, 근거없음 거르기 19→18/20.
# 0.50 이하는 정답 1개 더 늘지만 오답·거르기 실패가 함께 늘었다. 답할지 말지는 A.X가 "찾을 수 없습니다"로 한 번 더 거른다.
MIN_SCORE = float(os.getenv("ASK_MIN_SCORE", "0.55"))
FAQ_SCORE = float(os.getenv("ASK_FAQ_SCORE", "0.75"))       # 이 이상이면 FAQ 답변을 그대로 사용
SAME_QUESTION = float(os.getenv("ASK_SAME_QUESTION", "0.85"))  # 답변 대기에서 같은 질문으로 묶는 기준 (FR-028)
PENDING_DAYS = 30         # 답변 대기 만료 (AVL-008)

# 관리 웹 임시 로그인. 이메일 인증 코드(FR-033)는 발송 계정이 정해진 뒤 붙인다.
ADMIN_PASSWORD = os.getenv("ASK_ADMIN_PASSWORD", "")
SECRET = os.getenv("ASK_SECRET", "dev-only-change-me")
