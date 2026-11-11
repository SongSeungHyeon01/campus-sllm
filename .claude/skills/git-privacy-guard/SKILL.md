---
name: git-privacy-guard
description: 사용자의 개인정보·비밀값(이메일, 비밀번호, 와이파이 비번, API 키·토큰, OAuth 클라이언트 ID, 공인 IP, MAC, Oracle OCID·계정명, 로컬 사용자 경로, 전화번호, .env·.pem·db 파일)이 git 커밋·푸시·PR·공개 리포에 들어가지 않게 검사하고 막는다. git commit, git push, PR 생성, 리포 공개 전환, "깃에 올려", "푸시해", "커밋해", 코드 업로드·공유를 할 때마다 반드시 먼저 사용한다. 설정 파일(.env, netplan, config)을 출력·인용할 때 비밀값을 가리는 규칙도 여기 있다. 사용자가 "개인정보", "비밀번호 노출", "깃에 안 들어가게"를 언급하면 반드시 사용한다.
---

# git-privacy-guard

사용자는 "깃에 올릴 때 내 개인정보 절대로 올리면 안 된다"고 분명히 했다. 공개 리포에 한 번 올라간 값은 지워도 과거 커밋·포크·캐시에 남기 때문에, **올리기 전에** 막는 게 유일하게 확실한 방법이다. 이 스킬은 그 확인을 습관이 아니라 절차로 만든다.

## 구성 (이미 설치돼 있어야 하는 것)

| 구성 | 위치 | 역할 |
|---|---|---|
| 검사기 | `.claude/skills/git-privacy-guard/scripts/privacy_scan.py` (이 리포) | 추가된 줄만 검사, 찾은 값은 앞 3글자만 보여주고 가림 |
| 리포 훅 | `.githooks/pre-commit`, `pre-push` (이 리포) | 커밋·푸시 직전에 검사기를 자동 실행 |
| 개인 목록 | `~/.config/git-privacy/personal.txt` | 각자의 고유 문자열(본명, 개인 이메일, 학번 등)·허용 규칙. **어떤 리포에도 넣지 않는다** |

> 이 파일은 송승현의 전역 스킬을 물어봐 캠퍼스 리포용으로 복사한 것이다. 경로만 리포 기준으로 바꿨다.

작업 시작 전에 한 번 확인한다 (리포 폴더에서):

```bash
git config --get core.hooksPath            # .githooks 여야 훅이 동작
git config --get user.email                # GitHub noreply 주소여야 커밋 작성자 이메일이 안 드러남
```

둘 중 하나라도 아니면 사용자에게 알리고 아래 "처음 설정"을 안내한다. 전역 git 설정 변경은 사용자 승인이 필요할 수 있으니 직접 바꾸지 못하면 명령을 건네준다.

## 커밋·푸시할 때의 절차

1. **스테이징한 뒤 검사기를 먼저 돌린다.** 훅이 어차피 돌지만, 미리 돌리면 막혔을 때 원인을 바로 고칠 수 있다.
   ```bash
   PYTHONIOENCODING=utf-8 python .claude/skills/git-privacy-guard/scripts/privacy_scan.py staged
   ```
2. **푸시 전에는 올라갈 커밋 전체를 검사한다.** 커밋 작성자 이메일과 커밋 메시지까지 본다.
   ```bash
   PYTHONIOENCODING=utf-8 python .claude/skills/git-privacy-guard/scripts/privacy_scan.py range origin/<브랜치>..HEAD
   ```
3. 리포를 **공개로 바꾸거나 처음 올리기 전**에는 파일 전체를 본다: `privacy_scan.py tree HEAD`
4. 걸린 항목이 있으면 아래 "고치는 법"으로 해결하고 다시 검사한다. 통과하기 전엔 커밋·푸시하지 않는다.

`--no-verify`로 훅을 건너뛰지 않는다. 훅이 막았다면 그건 고쳐야 할 신호지 우회할 장애물이 아니다. 오탐이라고 판단되면 사용자에게 무엇이 걸렸는지 보여주고 허용 여부를 묻는다.

## 고치는 법

| 걸린 것 | 해결 |
|---|---|
| 비밀번호·키·토큰 | 코드에서 빼고 `.env`(gitignore) 또는 환경변수로 읽는다. 실제 값이 이미 푸시됐다면 **값 자체를 교체**(재발급)하라고 사용자에게 알린다 — 지우는 것만으론 부족하다 |
| OCID·계정명·서브넷 ID 등 계정 식별자 | 실행할 때 이름으로 조회하게 바꾼다 (예: `list_subnets(display_name=...)`) |
| 로컬 경로 `C:\Users\<이름>` | `os.path.expanduser("~/...")`, `%USERPROFILE%`, `$HOME`으로 |
| 문서 예시의 IP | 문서 전용 대역 `192.0.2.x`, `198.51.100.x`, `203.0.113.x`를 쓴다 |
| 이메일 | 예시는 `@example.com`. 실제 운영 값(관리자 이메일 등)은 `.env`로 |
| 커밋 작성자 이메일 | `git config --global user.email <noreply>`. 아직 안 올린 커밋은 `git rebase --autostash <원격브랜치> --exec "git commit --amend --no-edit --reset-author"`로 작성자를 바꾼다(이미 푸시된 커밋은 손대지 않음) |
| `.env`, `.pem`, `*.db`, `known_hosts` 등 파일 | `git rm --cached <파일>` 후 `.gitignore`에 추가 |

**이미 푸시된 것**을 이력에서 지우려면 강제 푸시(이력 재작성)가 필요하다. 팀원 복사본과 어긋나고 되돌리기 어려우므로, 무엇이 노출됐는지·위험도(자격 증명인지 식별자인지)를 설명하고 **사용자가 명시적으로 원할 때만** 한다.

## 출력할 때도 가린다

이 대화 기록 자체도 남는다. 서버 설정 파일(netplan, `.env`, `~/.oci/config` 등)을 확인할 때 원문을 그대로 출력하지 않는다. 처음부터 가려서 본다:

```bash
sudo sed -E 's/((password|secret|token|key)[^:=]*[:=]\s*).*/\1(숨김)/I' /etc/netplan/*.yaml
```

과거에 netplan을 그대로 출력해 와이파이 비밀번호가 기록에 남은 적이 있다. 같은 실수를 반복하지 않는 게 이 규칙의 이유다.

## 개인 목록 관리

- 고유 문자열 추가: `~/.config/git-privacy/personal.txt`에 한 줄로 적는다(대소문자 무시).
- 평문으로 적으면 안 되는 값(와이파이·계정 비밀번호): 사용자가 직접 실행하게 한다. 값은 해시로만 저장된다.
  ```bash
  python .claude/skills/git-privacy-guard/scripts/privacy_scan.py add-secret
  ```
  Claude가 그 값을 대신 입력받거나 명령줄에 쓰지 않는다 — 그러면 기록에 남는다.
- 허용 규칙: `allow:<정규식>` (예: 사용자의 noreply 주소). 특정 줄만 예외로 할 땐 그 줄에 `privacy-allow` 주석.

## 처음 설정 (clone한 뒤 리포 폴더에서 한 번)

```bash
git config core.hooksPath .githooks
git config user.email "<GitHub ID>+<사용자명>@users.noreply.github.com"
```

noreply 주소는 GitHub 웹 설정 → Emails 화면에 나온다.

GitHub 웹 설정 → Emails에서 **Keep my email addresses private**와 **Block command line pushes that expose my email**도 켜 두면 실수로 개인 메일이 박힌 커밋을 GitHub 쪽에서도 거부한다.
