# transformers 5.x가 Kanana 1.5 2.1B 설정 파일을 거부해 서버가 시작되지 않음

- **발생 시각**: 2026-10-12
- **위치**: `ask-campus/src/server/llm.py` → `AutoTokenizer.from_pretrained("kakaocorp/kanana-1.5-2.1b-instruct-2505")`, 서버 시작(lifespan)
- **상태**: 해결됨

## 증상

`uvicorn src.server.app:app` 실행 시 모델을 올리는 단계에서 종료.

```
huggingface_hub.errors.StrictDataclassClassValidationError: Class validation error for validator 'validate_architecture':
    ValueError: The hidden size (1792) is not a multiple of the number of attention heads (24).
ERROR:    Application startup failed. Exiting.
```

## 원인 조사

- `pip install transformers`로 최신판(5.19.0)이 설치되어 있었다.
- 모델 설정을 transformers 4.57.6으로 읽어 보니 `model_type=llama, hidden_size=1792, num_attention_heads=24, head_dim=128`. 즉 Kanana는 `head_dim`을 따로 정해 두는 구조(24 × 128 ≠ 1792)다.
- transformers 5.x는 설정 클래스에 엄격한 검사(`validate_architecture`)를 넣어 hidden_size가 head 수로 나누어떨어지지 않으면 거부한다. 4.x는 `head_dim`을 그대로 받아들인다.

## 근본 원인

transformers 5.x의 설정 검사와 Kanana 1.5 설정(`head_dim` 별도 지정)이 맞지 않음.

## 해결 방법

- `transformers>=4.51,<5`로 고정 (4.57.6 설치).
- 그러자 sentence-transformers 6.1.0이 `transformers>=5`를 요구해 충돌 → `sentence-transformers>=3.4,<6`(5.7.0)으로 맞춤. `pip check` 통과.
- 고정한 버전은 `ask-campus/requirements.txt`에 적었다.

## 재발 방지

- 서버 패키지는 `ask-campus/requirements.txt`의 고정 버전으로 설치한다. transformers를 5.x로 올리려면 Kanana 쪽 대응(모델 카드·설정 갱신)을 먼저 확인한다.
