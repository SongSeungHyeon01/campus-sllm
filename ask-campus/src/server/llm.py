"""sLLM 답변 생성 (FR-003). Kanana 1.5 2.1B Instruct를 GPU에서 bf16으로 띄운다 (약 4.5GB)."""
import re
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
    "5. 지금은 {today}입니다. '오늘', '이번 주', '지금', '방금', '다음', '가장 빠른' 같은 표현은 이 시각을 기준으로 판단합니다.\n"
    "6. 시간표에서 '가장 빠른'·'다음'·'지금 탈 수 있는' 차를 물으면, 질문한 정류장의 시간 중 지금 시각 이후 가장 가까운 시간을 "
    "회차·호차와 함께 답합니다. 이미 지난 시간은 답하지 않습니다."
)


@lru_cache(maxsize=1)
def _model():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(config.LLM_MODEL)
    kw = {}
    if config.LLM_QUANT in ("4bit", "8bit"):    # 3B 넘는 모델은 bf16이면 8GB GPU에 KURE와 같이 안 올라감
        from transformers import BitsAndBytesConfig
        kw["quantization_config"] = (
            BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16)
            if config.LLM_QUANT == "4bit" else BitsAndBytesConfig(load_in_8bit=True))
    model = AutoModelForCausalLM.from_pretrained(
        config.LLM_MODEL, dtype=torch.bfloat16, device_map="cuda" if torch.cuda.is_available() else "cpu", **kw)
    model.eval()
    return tok, model


def ready() -> bool:
    return _model.cache_info().currsize > 0


def warm_up():
    """모델을 올리고 짧게 한 번 생성해 둔다. 첫 생성은 GPU 초기화로 15초 넘게 걸려서 서버 시작 때 미리 치른다."""
    _model()
    answer("안녕하세요", ["물어봐 캠퍼스 시험 문장"], "2026년 1월 1일")


# 11/10 모델 비교: "제공되지 않았습니다"(Midm), "존재하지 않습니다"(Kanana-2)처럼 다르게 말하면 답변 대기에 안 올라가서 추가
_NOT_FOUND_HINTS = (NOT_FOUND, "찾을 수 없", "자료에 없", "자료에는 없", "확인할 수 없", "알 수 없습니다", "나와 있지 않",
                    "제공되지 않", "존재하지 않", "언급되어 있지 않", "포함되어 있지 않", "정보가 없")


def is_not_found(text: str) -> bool:
    """sLLM이 근거가 없다고 답했는지. 표현이 조금씩 달라서 여러 문구로 확인한다."""
    return any(h in text for h in _NOT_FOUND_HINTS)


# "연락처: 010-"처럼 값이 비었거나 번호 앞자리만 남은 항목 (자료의 빈 칸을 그대로 옮긴 경우)
_EMPTY_FIELD = re.compile(r"^[-·*\s]*[가-힣A-Za-z ]{1,12}\s*[:：]\s*(0\d{1,2}\s*-?\s*)?$")
# 규칙 4에서 금지했는데도 붙는 맺음말. 짧은 줄에서만 지운다
_CLOSING = re.compile(r"궁금한 (점|사항)|추가로 (궁금|문의)|문의 주세요|감사합니다|도움이 되(셨|었)|말씀해 주세요")
_HTML = re.compile(r"</?[A-Za-z][^>]*>")


def _clean(text: str) -> str:
    """자료 형식을 따라 쓴 줄('[자료]', '■ …'), 빈 항목, 맺음말, HTML 태그를 지운다."""
    text = _HTML.sub("", text)
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith(("[자료]", "[질문]", "■")) or _EMPTY_FIELD.match(s):
            continue
        if len(s) <= 40 and _CLOSING.search(s):
            continue
        lines.append(ln.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def answer(question: str, contexts: list[str], today: str) -> str:
    import torch
    tok, model = _model()
    # 근거는 system 메시지에 넣는다. user 메시지에 '[자료] (1) …' 형식으로 넣었더니 답변이 그 형식을 따라 써서 바꿈
    material = "\n\n".join(f"■ {c}" for c in contexts)
    messages = [
        {"role": "system", "content": SYSTEM.format(today=today) + "\n\n[자료]\n" + material},
        {"role": "user", "content": question},
    ]
    # enable_thinking=False: Qwen3 계열은 기본으로 <think> 추론을 먼저 써서 끈다 (이 변수를 안 쓰는 템플릿은 무시함)
    ids = tok.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt",
                                  enable_thinking=False).to(model.device)
    with torch.no_grad():
        out = model.generate(ids, max_new_tokens=200, do_sample=False, repetition_penalty=1.05,
                             pad_token_id=tok.eos_token_id)
    return _clean(tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True).strip())
