"""sLLM 답변 생성 (FR-003). Kanana 1.5 2.1B Instruct를 GPU에서 bf16으로 띄운다 (약 4.5GB)."""
from functools import lru_cache

from . import config

NOT_FOUND = "해당 정보를 찾을 수 없습니다."

SYSTEM = (
    "당신은 유원대학교 학생을 돕는 '물어봐 캠퍼스' 안내 도우미입니다.\n"
    "규칙:\n"
    "1. 반드시 아래 [자료]에 적힌 내용만으로 답합니다. 자료에 없는 내용은 추측하지 않습니다.\n"
    f"2. 자료로 답할 수 없으면 다른 말 없이 \"{NOT_FOUND}\"라고만 답합니다.\n"
    "3. 날짜·시간·금액·장소는 자료에 적힌 그대로 씁니다.\n"
    "4. 한국어 존댓말로 1~4문장 안에서 질문에 필요한 내용만 답합니다. 자료 번호, 인사말, '추가로 궁금한 점' 같은 맺음말은 쓰지 않습니다.\n"
    "5. 오늘 날짜는 {today}입니다. '이번 주', '오늘까지' 같은 표현은 이 날짜를 기준으로 판단합니다."
)


@lru_cache(maxsize=1)
def _model():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(config.LLM_MODEL)
    model = AutoModelForCausalLM.from_pretrained(
        config.LLM_MODEL, dtype=torch.bfloat16, device_map="cuda" if torch.cuda.is_available() else "cpu")
    model.eval()
    return tok, model


def ready() -> bool:
    return _model.cache_info().currsize > 0


def warm_up():
    """모델을 올리고 짧게 한 번 생성해 둔다. 첫 생성은 GPU 초기화로 15초 넘게 걸려서 서버 시작 때 미리 치른다."""
    _model()
    answer("안녕하세요", ["물어봐 캠퍼스 시험 문장"], "2026년 1월 1일")


_NOT_FOUND_HINTS = (NOT_FOUND, "찾을 수 없", "자료에 없", "자료에는 없", "확인할 수 없", "알 수 없습니다", "나와 있지 않")


def is_not_found(text: str) -> bool:
    """sLLM이 근거가 없다고 답했는지. 표현이 조금씩 달라서 여러 문구로 확인한다."""
    return any(h in text for h in _NOT_FOUND_HINTS)


def _clean(text: str) -> str:
    """자료 형식을 그대로 따라 쓴 줄('[자료]', '(1) …')을 지운다."""
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith(("[자료]", "[질문]", "■"))]
    return "\n".join(lines).strip()


def answer(question: str, contexts: list[str], today: str) -> str:
    import torch
    tok, model = _model()
    # 근거는 system 메시지에 넣는다. user 메시지에 '[자료] (1) …' 형식으로 넣었더니 답변이 그 형식을 따라 써서 바꿈
    material = "\n\n".join(f"■ {c}" for c in contexts)
    messages = [
        {"role": "system", "content": SYSTEM.format(today=today) + "\n\n[자료]\n" + material},
        {"role": "user", "content": question},
    ]
    ids = tok.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(ids, max_new_tokens=200, do_sample=False, repetition_penalty=1.05,
                             pad_token_id=tok.eos_token_id)
    return _clean(tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True).strip())
