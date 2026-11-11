# Hermes Agent × Campus sLLM 활용 정리

> 작성일: 2026-10-27
> 출처: GitHub README와 공식 문서(아래 링크)를 읽고 정리함. 직접 설치해서 돌려보지는 않았음.

## 1. Hermes Agent가 뭔가

- **GitHub**: https://github.com/NousResearch/hermes-agent
- **공식 문서**: https://hermes-agent.nousresearch.com/docs/
- **만든 곳**: Nous Research (Hermes 계열 오픈 모델 개발사)
- **라이선스**: MIT
- **한 줄 요약**: 스스로 학습하는 범용 AI 에이전트. 터미널 에이전트(Claude Code·Codex CLI와 비슷)에 메신저 연동, 장기 기억, 스킬 자동 생성, 예약 작업이 붙어 있음.
- **주요 기능**
  - 도구 40개 이상, MCP 지원, 서브에이전트 병렬 실행
  - 실행 환경: 로컬, Docker, SSH, Modal, Daytona, Vercel Sandbox
  - Telegram·Discord·Slack 등 메신저 게이트웨이, cron 예약 작업
  - **특정 모델에 묶이지 않음**: OpenAI 호환 엔드포인트면 무엇이든 연결 가능
  - **연구용 기능**: 도구 호출 학습 데이터(trajectory)를 대량 생성

Campus sLLM에 쓸모 있는 건 아래 두 가지.

---

## 2. 활용 ① 직접 띄운 sLLM을 에이전트로 테스트하기

직접 학습하거나 서빙한 sLLM을 Hermes의 "두뇌"로 연결해서, **실제 에이전트 환경에서 도구를 제대로 쓰는지** 확인하는 테스트베드로 쓸 수 있다.

### 연결 방법

`hermes model`을 실행해 custom endpoint를 고르거나, `config.yaml`을 직접 고친다.

```yaml
model:
  default: <모델 이름>
  provider: custom
  base_url: http://localhost:8000/v1   # 서빙 서버 주소
  api_key:                             # 로컬이면 비워도 됨
  context_length: 64000
```

- 대화 중 모델 바꾸기: `/model custom:<모델명>`
- 엔드포인트 여러 개: `providers:` 아래에 이름을 붙여 등록하고 `/model custom:<이름>:<모델>`로 전환

### 서빙 서버별 필수 옵션 (도구 호출용)

이 옵션이 빠지면 도구 호출이 그냥 텍스트로 나와서 에이전트가 동작하지 않는다.

| 서버 | 기본 포트 | 도구 호출 필수 옵션 | 컨텍스트 설정 |
|---|---|---|---|
| vLLM | 8000 | `--enable-auto-tool-choice --tool-call-parser <파서>` (`hermes`, `llama3_json`, `mistral` 등) | `--max-model-len 65536` |
| SGLang | 30000 | `--tool-call-parser <파서>` (`qwen`, `llama3` 등) | `--context-length 65536`, 출력이 잘리면 `--default-max-tokens` |
| llama.cpp | 8080 | `--jinja` | `-c 64000` (`-np`로 슬롯을 나누면 슬롯마다 컨텍스트가 줄어듦) |
| Ollama | 11434 | 기본 켜짐 (`ollama show`로 지원 여부 확인) | `OLLAMA_CONTEXT_LENGTH=64000` 또는 Modelfile에 `num_ctx` |
| LM Studio | 1234 | 0.3.6 이상 | `--context-length 64000` |

### ⚠️ sLLM이라서 걸리는 점

- **컨텍스트 64K 미만이면 시작 단계에서 거부된다.** 공식 문서에 명시된 최소 조건. 작은 모델이 64K를 지원하지 않으면 이 용도로는 못 씀.
- 작은 모델은 도구 전체 목록과 긴 시스템 프롬프트를 감당하기 어렵다. **도구셋을 줄여서** 테스트하는 게 권장된다.
- 모델의 chat template이 도구 호출 형식을 지원해야 하고, 서빙 서버의 파서 설정과 맞아야 한다.

---

## 3. 활용 ② 도구 사용 파인튜닝용 학습 데이터 만들기

`batch_runner.py`로 프롬프트 목록을 에이전트에 대량으로 돌리고, 그 과정(생각 → 도구 호출 → 결과 → 답변)을 **ShareGPT 형식 JSONL**로 저장한다. 큰 모델로 데이터를 만들고, 그걸로 sLLM에 도구 사용 능력을 파인튜닝(지식 증류)하는 흐름에 바로 쓸 수 있다.

### 실행

```bash
python batch_runner.py \
  --dataset_file=data/prompts.jsonl \
  --batch_size=10 \
  --run_name=my_first_run \
  --num_workers=4
```

- 입력 `prompts.jsonl`: 한 줄에 `{"prompt": "..."}` 하나. 선택 필드로 `docker_image`, `cwd`
- 주요 옵션: `--model`, `--base_url`(데이터를 만들 "선생" 모델), `--max_turns`(기본 10), `--distribution`(도구셋 조합 샘플링), `--max_samples`
- 중단되면 `--resume`으로 이어서 실행. 실패한 프롬프트는 재시도된다.
- 결과 위치: `data/<run_name>/trajectories.jsonl` (+ `statistics.json`에 도구 사용 통계)

### 출력 형식 (ShareGPT 호환)

```json
{
  "conversations": [
    {"from": "system", "value": "...<tools>도구 정의 JSON</tools>..."},
    {"from": "human",  "value": "사용자 질문"},
    {"from": "gpt",    "value": "<think>...</think>\n<tool_call>{\"name\": ..., \"arguments\": {...}}</tool_call>"},
    {"from": "tool",   "value": "<tool_response>{\"tool_call_id\": ..., \"name\": ..., \"content\": ...}</tool_response>"},
    {"from": "gpt",    "value": "<think>...</think>\n최종 답변"}
  ],
  "completed": true,
  "metadata": {"model": "..."},
  "tool_stats": {...}
}
```

- 모든 `gpt` 턴에 `<think>` 블록이 들어간다(비어 있어도 들어감).
- 도구 호출은 `<tool_call>`, 결과는 `<tool_response>` 태그. Hermes 계열 모델의 함수 호출 형식이다.
- 추론(reasoning)이 하나도 없는 샘플과 잘못된 도구 이름이 들어간 샘플은 자동으로 걸러진다.
- 학습에 바로 쓰기 좋은 필터 기준: `completed: true`, `tool_error_counts`가 적은 것

### ⚠️ 걸리는 점

- 선생 모델 API 비용이 든다(기본값 `claude-sonnet-4.6`, `--model`/`--base_url`로 변경 가능). 프롬프트 수 × 최대 턴 수만큼 호출되므로 `--max_samples`로 작게 시작할 것.
- 학습할 sLLM의 chat template이 `<tool_call>` 형식과 다르면 변환 스크립트가 필요하다.
- README는 "trajectory compression"(긴 궤적 압축)과 Atropos RL 학습도 언급하지만, 공식 문서에 별도 사용법 페이지는 확인하지 못했다. 쓰려면 저장소 코드를 직접 봐야 한다.

---

## 4. 추천 순서

1. sLLM을 vLLM 등으로 띄우고 **컨텍스트 64K가 되는지**부터 확인한다. 안 되면 활용 ①은 보류.
2. Hermes에 custom endpoint로 연결하고 **도구셋을 줄여서** 간단한 작업(파일 읽기, 검색 등)을 시켜본다.
3. 도구 사용이 약하면 → 큰 모델로 `batch_runner.py`를 소량(예: 50~100개) 돌려 데이터 형식을 확인한다.
4. 형식을 sLLM 템플릿에 맞게 변환해서 파인튜닝하고, 2번 테스트로 다시 비교한다.

## 참고 링크

- 저장소: https://github.com/NousResearch/hermes-agent
- 모델/엔드포인트 연결: https://hermes-agent.nousresearch.com/docs/integrations/providers
- 배치 처리(batch_runner): https://hermes-agent.nousresearch.com/docs/user-guide/features/batch-processing
- 궤적 형식: https://hermes-agent.nousresearch.com/docs/developer-guide/trajectory-format
- 설정: https://hermes-agent.nousresearch.com/docs/user-guide/configuration
