# Kanana-2 모델 다운로드가 수십 MB에서 멈춤

- **발생 시각**: 2026-11-10
- **위치**: `huggingface_hub.snapshot_download('kakaocorp/kanana-2-3b-instruct')` (ask-campus/.venv, huggingface_hub 0.36.2, hf-xet 1.7.0)
- **상태**: 우회함

## 증상
- 같은 명령으로 Midm-2.0-Mini(4.4GB)는 정상으로 받아짐.
- Kanana-2(7.0GB)는 아래처럼 멈춤.
  - 1차: `.incomplete` 파일이 64MB에서 멈췄고, 진행률은 `Fetching 9 files: 33%`에서 그대로였음.
  - 2차: 다시 시작했지만 약 10MB에서 30초 넘게 크기가 늘지 않음.
- 오류 메시지는 없었음. 프로세스가 끝나지도 않음.

## 원인 조사
- 디스크 공간은 원인이 아님(여유 1.6TB).
- 네트워크도 원인이 아님. 같은 세션에서 Midm은 받아졌음.
- 2차 시도에서 `HF_HUB_DOWNLOAD_TIMEOUT=60`을 주고 동시 다운로드를 2개(`max_workers=2`)로 줄였지만 효과 없었음.
- 3차 시도에서 `HF_HUB_DISABLE_XET=1`로 Xet 전송을 끄고 일반 HTTP로 받음. 초당 약 15~20MB로 진행됐고, 몇 분 뒤 완료됨.

## 근본 원인
미확인. 가장 유력한 가설은 hf-xet 1.7.0의 Xet 전송이 이 저장소에서 멈춘 것임. Windows 심볼릭 링크 미지원 경고는 이전 모델에서도 나왔으므로 원인은 아닌 것으로 봄.

## 해결 방법
`HF_HUB_DISABLE_XET=1`을 설정한 뒤 다시 받음. 이미 받은 파일은 그대로 쓸 수 있음.

## 재발 방지
- 큰 모델을 받을 때 1분 동안 크기가 늘지 않으면 바로 `HF_HUB_DISABLE_XET=1`로 다시 받음.
