"""sLLM 답변 생성 (FR-003). A.X 4.0 Light(7B)를 GPU에서 4bit로 띄운다 (약 5~6GB)."""
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
    "회차·호차와 함께 답합니다. 이미 지난 시간은 답하지 않습니다.\n"
    "7. '[학생 Q&A]' 자료는 예전에 한 학생에게 한 답변입니다. 공지·학사일정·FAQ와 다르면 공지·학사일정·FAQ를 따르고, "
    "특정 학생 개인의 사정에 대한 답변은 일반 안내처럼 쓰지 않습니다.\n"
    "8. 같은 행사·일정이 여러 해 자료에 있으면, 질문에 연도가 없는 한 지금 이후의 가장 가까운 일정으로 답합니다.\n"
    "9. 마크다운 기호(**, ##, `)와 이모지는 쓰지 않고 평범한 문장으로 답합니다. 여러 항목은 한 줄에 하나씩 씁니다.\n"
    "10. '있어?', '뭐 있어?', '누구 있어?'처럼 무엇이 있는지 묻는 질문에는 이름만 한 줄로 답합니다 (예: 'C.C.C, S.F.C가 있습니다.'). "
    "목적·활동 같은 설명은 '뭐 하는 곳이야?', '어떤 동아리야?'처럼 그것을 물을 때만 씁니다.\n"
    "11. 자료가 질문과 다른 대상에 관한 것이면(예: 통학버스를 물었는데 자료는 시내버스, 성적장학금을 물었는데 다른 장학금) "
    "그 자료의 숫자를 옮기지 말고 '찾을 수 없습니다'라고 답합니다."
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
    if config.LLM_ADAPTER:                      # LoRA 어댑터 (예: RAG 행동을 추가 학습한 어댑터)
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, config.LLM_ADAPTER)
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
                    "제공되지 않", "존재하지 않", "언급되어 있지 않", "포함되어 있지 않", "정보가 없", "찾지 못했", "정보는 없")


def is_not_found(text: str) -> bool:
    """sLLM이 근거가 없다고 답했는지. 표현이 조금씩 달라서 여러 문구로 확인한다."""
    return any(h in text for h in _NOT_FOUND_HINTS)


# "연락처: 010-"처럼 값이 비었거나 번호 앞자리만 남은 항목 (자료의 빈 칸을 그대로 옮긴 경우)
_EMPTY_FIELD = re.compile(r"^[-·*\s]*([가-힣A-Za-z ]{1,12}\s*[:：]\s*)?(0\d{1,2}[\s-]*)?$")
# 11/18 기준값 0.55 시험: 한맥 연락처를 물으니 답 전체가 "010--"였다 (번호 앞자리만 남은 경우)
_PHONE_STUB = re.compile(r"(?<![\d:.])0\d{1,2}\s*-+(?=\s*(?:$|[^\d\s]))", re.M)
# 규칙 4에서 금지했는데도 붙는 맺음말. 짧은 줄에서만 지운다
_CLOSING = re.compile(r"궁금한 (점|사항)|추가로 (궁금|문의)|문의 주세요|감사합니다|도움이 되(셨|었)|말씀해 주세요")
_HTML = re.compile(r"</?[A-Za-z][^>]*>")
# 11/19 사용자 요청: '**11월 16일 (월)**'처럼 AI 티가 나는 마크다운·이모지를 지운다
_MD_EMPHASIS = re.compile(r"(\*\*|__|`)")
_MD_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*")
_MD_BULLET = re.compile(r"^(\s*)[-*+]\s+")
_EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF️]")


def _clean(text: str) -> str:
    """자료 형식을 따라 쓴 줄('[자료]', '■ …'), 빈 항목, 맺음말, HTML 태그를 지운다."""
    text = _HTML.sub("", text)
    text = _PHONE_STUB.sub("", text)
    text = _EMOJI.sub("", _MD_EMPHASIS.sub("", text))
    lines = []
    for ln in text.splitlines():
        ln = _MD_BULLET.sub(r"\1· ", _MD_HEADING.sub("", ln))   # '- 항목' → '· 항목', '### 제목' → '제목'
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
