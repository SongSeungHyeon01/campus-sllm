"""서버 설정. 값은 환경 변수로 바꿀 수 있다."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # ask-campus/
DATA = ROOT / "data"
DB_PATH = Path(os.getenv("ASK_DB", DATA / "askcampus.db"))
CHROMA_DIR = Path(os.getenv("ASK_CHROMA", DATA / "chroma"))
CHUNKS_JSONL = DATA / "chunks.jsonl"

EMBED_MODEL = os.getenv("ASK_EMBED_MODEL", "nlpai-lab/KURE-v1")
LLM_MODEL = os.getenv("ASK_LLM_MODEL", "kakaocorp/kanana-1.5-2.1b-instruct-2505")
EMBED_DEVICE = os.getenv("ASK_EMBED_DEVICE", "cuda")  # "cpu"면 KURE를 CPU에서 돌림
LLM_QUANT =os.getenv("ASK_LLM_QUANT", "")          # ""(bf16) | "4bit" | "8bit"
USE_LLM =os.getenv("ASK_USE_LLM", "1") == "1"       # 0이면 sLLM 없이 근거 문장만 돌려줌 (GPU 없는 PC에서 시험용)

TOP_K = 5                 # 벡터 검색 개수 (FR-002)
CONTEXT_K = 3             # sLLM에 넘기는 근거 수, 출처 표시도 최대 3개 (FR-004)
MIN_SCORE = float(os.getenv("ASK_MIN_SCORE", "0.60"))       # 이보다 낮으면 근거 없음 (FR-005). 10/12 시험: 답 있는 질문 0.63~0.82, 없는 질문 0.47~0.61. 테스트 질문셋 80개로 다시 조정
FAQ_SCORE = float(os.getenv("ASK_FAQ_SCORE", "0.75"))       # 이 이상이면 FAQ 답변을 그대로 사용
SAME_QUESTION = float(os.getenv("ASK_SAME_QUESTION", "0.85"))  # 답변 대기에서 같은 질문으로 묶는 기준 (FR-028)
PENDING_DAYS = 30         # 답변 대기 만료 (AVL-008)

# 관리 웹 임시 로그인. 이메일 인증 코드(FR-033)는 발송 계정이 정해진 뒤 붙인다.
ADMIN_PASSWORD = os.getenv("ASK_ADMIN_PASSWORD", "")
SECRET = os.getenv("ASK_SECRET", "dev-only-change-me")
