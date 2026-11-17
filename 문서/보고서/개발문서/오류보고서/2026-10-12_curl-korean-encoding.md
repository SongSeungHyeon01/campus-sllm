# Git Bash의 curl로 보낸 한글이 깨져 FAQ가 이상한 글자로 저장되고 JSON 요청이 400

- **발생 시각**: 2026-10-12
- **위치**: 시험 명령 (Git Bash `curl -d` / `--data-urlencode`) → `POST /admin/pending/{id}/answer`, `POST /api/v1/ask`
- **상태**: 우회함 (시험은 Python 클라이언트로)

## 증상

- curl로 답변을 등록한 FAQ의 질문·답변이 `���Ի� ����…`처럼 저장됨.
- curl로 한글 JSON을 보낸 `/api/v1/ask` 요청이 `{"detail":"There was an error parsing the body"}`(400).
- 같은 서버에 Python `urllib`(UTF-8)로 보내면 정상.

## 원인 조사

- 서버 쪽 문제인지 확인하려고 Python으로 같은 요청을 보냄 → 정상 → 서버가 아니라 보내는 쪽 문제.
- 이 PC의 Git Bash에서 curl 인자로 넘긴 한글이 UTF-8이 아닌 콘솔 인코딩(CP949로 추정)으로 전달되었다 (가설).

## 근본 원인

시험 도구(Windows Git Bash + curl)의 인자 인코딩. 브라우저와 앱은 항상 UTF-8로 보내므로 실제 사용에는 영향이 없다.

## 해결 방법

- 깨진 FAQ 1건을 지우고 해당 답변 대기를 '대기'로 되돌렸다.
- 한글이 들어가는 시험은 `scripts/smoke_test.py`, `scripts/e2e_test.py`(Python)로 한다.
- 앱 자동 시험도 같은 이유로 `adb input text`(한글 불가) 대신 디버그 빌드 전용 Base64 인텐트(`q64`)를 쓴다.

## 재발 방지

- Windows에서 한글 요청 시험은 Python 스크립트로 한다. curl을 꼭 써야 하면 본문을 UTF-8 파일로 저장해 `--data-binary @file`로 보낸다.
