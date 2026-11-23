"""학교 자료를 다시 수집하고 색인을 새로 만든다. Windows 작업 스케줄러가 주기적으로 실행한다.

사용 (ask-campus 폴더에서):
  .venv/Scripts/python scripts/refresh.py daily    # 공지(게시판마다 최근 60건)·학사일정·통학버스·동아리 (매일)
  .venv/Scripts/python scripts/refresh.py weekly   # 위 + 학교 FAQ·Q&A + 사이트 전체·학과·구내식당 (매주 월요일)

- 수집 중 하나가 실패해도 이전 결과 파일을 그대로 두고 나머지를 진행한다 (수집기는 끝날 때만 파일을 덮어씀).
- 서버가 켜져 있으면 서버에 색인을 다시 만들라고 요청하고(/internal/reindex), 꺼져 있으면 여기서 직접 만든다.
- 기록: data/logs/refresh.log
"""
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
LOG = ROOT / "data" / "logs" / "refresh.log"
SERVER = "http://127.0.0.1:8000"
JOBS = {
    # 수집한 뒤에는 늘 rescrub으로 이름·비밀번호 규칙을 다시 정리한다 (11/22)
    "daily": [["-m", "src.ingest.run", "--notice-pages", "6"], ["scripts/rescrub.py", "rescrub"]],
    "weekly": [["-m", "src.ingest.run", "--notice-pages", "6"], ["-m", "src.ingest.run_login"], ["-m", "src.ingest.run_site"],
               ["scripts/rescrub.py", "rescrub"]],
}


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def server_up() -> bool:
    try:
        with urllib.request.urlopen(SERVER + "/api/v1/health", timeout=5) as r:
            return json.load(r).get("status") == "ok"
    except Exception:
        return False


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "daily"
    if mode not in JOBS:
        print(__doc__)
        return 2
    log(f"=== {mode} 시작")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    for args in JOBS[mode]:
        r = subprocess.run([PY, *args], cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        tail = (r.stdout.strip().splitlines() or [""])[-1]
        log(f"{' '.join(args[1:])}: {'성공' if r.returncode == 0 else '실패'} {tail[:120]}")
        if r.returncode != 0:
            log("  " + (r.stderr.strip().splitlines() or ["(오류 내용 없음)"])[-1][:200])
    if server_up():
        token = (ROOT / "data" / ".reindex_token").read_text(encoding="utf-8")
        req = urllib.request.Request(SERVER + "/internal/reindex", method="POST", headers={"X-Reindex-Token": token})
        try:
            with urllib.request.urlopen(req, timeout=1800) as r:
                log(f"색인(서버 안): {json.load(r)}")
        except Exception as e:
            log(f"색인(서버 안) 실패: {e}")
            return 1
    else:
        r = subprocess.run([PY, "-m", "src.server.build_index"], cwd=ROOT, env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        log(f"색인(직접): {'성공' if r.returncode == 0 else '실패'} {(r.stdout.strip().splitlines() or [''])[-1][:120]}")
    log(f"=== {mode} 끝")
    return 0


if __name__ == "__main__":
    sys.exit(main())
