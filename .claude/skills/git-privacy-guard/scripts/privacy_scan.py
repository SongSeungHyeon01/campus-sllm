#!/usr/bin/env python3
"""privacy_scan.py — git에 개인정보·비밀값이 들어가기 전에 찾아낸다.

사용법
  python privacy_scan.py staged              커밋 직전(스테이징된 변경) 검사 — pre-commit 훅이 부른다
  python privacy_scan.py push                푸시될 커밋 검사(표준입력으로 ref 목록) — pre-push 훅이 부른다
  python privacy_scan.py range A..B          지정한 커밋 범위 검사
  python privacy_scan.py tree [REV]          REV(기본 HEAD)의 파일 전체 검사 — 공개 전 점검용
  python privacy_scan.py add-secret          비밀번호처럼 평문으로 적어둘 수 없는 값을 해시로 등록

찾은 값은 앞 몇 글자만 보여주고 나머지는 가린다. 검사 결과가 대화 기록·터미널 로그에 남아도
원래 값이 다시 새지 않게 하기 위해서다.

개인 목록: ~/.config/git-privacy/personal.txt (어떤 리포에도 넣지 않는다)
  한 줄에 하나. 그냥 쓰면 그 문자열(대소문자 무시)을, `sha256:<hex>`는 같은 해시를 가진 토큰을 찾는다.
  `allow:<정규식>`은 허용 목록(예: allow:@users\\.noreply\\.github\\.com$).
줄 단위 예외: 해당 줄에 `privacy-allow` 주석을 달면 그 줄은 건너뛴다.
"""

import getpass
import hashlib
import ipaddress
import os
import re
import subprocess
import sys

CONFIG = os.path.expanduser("~/.config/git-privacy/personal.txt")
ZERO = "0" * 40

# (이름, 정규식) — 값 자체가 비밀이거나 개인을 식별하는 것
RULES = [
    ("개인 키", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS 액세스 키", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub 토큰", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})")),
    ("Google API 키", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("Google OAuth 클라이언트 ID", re.compile(r"\b\d{8,}-[a-z0-9]{20,}\.apps\.googleusercontent\.com\b")),
    ("Google OAuth 시크릿", re.compile(r"\bGOCSPX-[A-Za-z0-9_\-]{20,}")),
    ("Slack 토큰", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}")),
    ("AI API 키", re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_\-]{20,}")),
    ("Oracle OCID", re.compile(r"\bocid1\.[a-z0-9]+\.oc1\.[a-z0-9\-]*\.[a-z0-9]{20,}")),
    ("주민등록번호", re.compile(r"(?<!\d)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])-[1-4]\d{6}(?!\d)")),
    ("휴대폰 번호", re.compile(r"(?<!\d)01[016789][-. ]?\d{3,4}[-. ]?\d{4}(?!\d)")),
    ("MAC 주소", re.compile(r"(?<![0-9A-Fa-f:])(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}(?![0-9A-Fa-f:])")),
    ("로컬 사용자 경로", re.compile(r"(?i)(?:[A-Z]:\\+Users\\+|/[a-z]/Users/)(?!Public\b|Default\b|<|\{|\$|%|USER|username|you\b)[^\\/\s\"'`]+")),
]

# nip.io/sslip.io처럼 도메인에 IP를 넣은 주소 — 안의 IP가 공인일 때만 잡는다(문서용 예시 대역 제외)
IP_DOMAIN = re.compile(r"\b(\d{1,3})[-.](\d{1,3})[-.](\d{1,3})[-.](\d{1,3})\.(?:nip|sslip)\.io\b")
# 패키지 버전(opencv==5.0.0.93, v1.2.3.4)을 IP로 착각하지 않도록 바로 앞 글자를 본다
VERSION_PREFIX = re.compile(r"(?i)(==|>=|<=|~=|!=|\^|~|\bv|version\s*[:=]?\s*[\"']?)$")

# 비밀번호류 키에 실제 값이 직접 적힌 경우(환경변수·자리표시자는 제외)
ASSIGN = re.compile(
    # \b 대신 (?<![a-z]) — DB_PASSWORD처럼 밑줄로 이어진 이름도 잡기 위해서
    r"(?i)(?<![a-z])(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|client[_-]?secret)"
    r"[\"']?\s*[:=]\s*[\"']?([^\s\"',;)}]{6,})"
)
PLACEHOLDER = re.compile(
    r"(?i)^(\$|<|\{|%|os\.|process\.|env\b|getenv|none|null|true|false|changeme|change-me|example|placeholder|"
    r"your[_-]|xxx|\*{3}|\.\.\.|password|secret|token|required|optional|str\b|string\b|self\.|settings\.|config\.)"
)

EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
DEFAULT_ALLOW = [
    r"@users\.noreply\.github\.com$",
    r"@example\.(com|org|net)$",
    r"^noreply@anthropic\.com$",
    r"@test\.com$",
    r"^(git|noreply|no-reply|admin|user|someone|name|you)@",
]

IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")

# 이름만으로 막는 파일
BLOCKED_FILES = re.compile(
    r"(?i)(^|/)(\.env(\.(?!example$|sample$|template$)[^/]+)?|[^/]*\.pem|[^/]*\.key|[^/]*\.p12|[^/]*\.pfx|"
    r"id_(rsa|ed25519|ecdsa|dsa)(\.pub)?|known_hosts|authorized_keys|credentials\.json|"
    r"[^/]*\.(db|sqlite|sqlite3)|\.oci/config|\.git-credentials|\.netrc)$"
)


def load_personal():
    literals, hashes, allows = [], set(), list(DEFAULT_ALLOW)
    if os.path.exists(CONFIG):
        with open(CONFIG, encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("sha256:"):
                    hashes.add(line[7:].strip().lower())
                elif line.startswith("allow:"):
                    allows.append(line[6:].strip())
                else:
                    literals.append(line.lower())
    return literals, hashes, [re.compile(a, re.I) for a in allows]


def mask(value):
    value = value.strip()
    if len(value) < 10:  # 짧은 값은 앞 3글자만으로도 거의 드러나므로 전부 가린다
        return "*" * len(value)
    return value[:3] + "*" * min(len(value) - 3, 12)


def public_ip(text):
    try:
        ip = ipaddress.ip_address(text)
    except ValueError:
        return False
    return ip.is_global


def scan_line(line, literals, hashes, allows):
    """한 줄에서 찾은 (규칙 이름, 가린 값) 목록."""
    if "privacy-allow" in line:
        return []
    hits = []
    for name, rx in RULES:
        for m in rx.finditer(line):
            hits.append((name, mask(m.group(0))))
    for m in ASSIGN.finditer(line):
        value = m.group(2)
        if not PLACEHOLDER.match(value):
            hits.append((f"{m.group(1)} 값", mask(value)))
    for m in EMAIL.finditer(line):
        addr = m.group(0)
        if not any(a.search(addr) for a in allows):
            hits.append(("이메일 주소", mask(addr)))
    for m in IPV4.finditer(line):
        if VERSION_PREFIX.search(line[max(0, m.start() - 12):m.start()]):
            continue
        if public_ip(m.group(0)):
            hits.append(("공인 IP", mask(m.group(0))))
    for m in IP_DOMAIN.finditer(line):
        if public_ip(".".join(m.group(1, 2, 3, 4))):
            hits.append(("IP가 들어간 도메인", mask(m.group(0))))
    low = line.lower()
    for lit in literals:
        if lit in low:
            hits.append(("개인 목록 항목", mask(lit)))
    if hashes:
        for tok in re.split(r"[\s\"'`=:,;()<>\[\]{}]+", line):
            if tok and hashlib.sha256(tok.encode("utf-8")).hexdigest() in hashes:
                hits.append(("등록한 비밀값", "***"))
    return hits


def git(*args, stdin=None):
    r = subprocess.run(["git", *args], capture_output=True, input=stdin)
    if r.returncode != 0:
        sys.stderr.write(r.stderr.decode("utf-8", "replace"))
        sys.exit(2)
    return r.stdout.decode("utf-8", "replace")


def scan_patch(patch, label, findings, ctx):
    """unified diff에서 추가된 줄(+)만 검사한다. 지워지는 줄은 문제가 아니다."""
    path = None
    lineno = 0
    for line in patch.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
            if path and BLOCKED_FILES.search(path):
                findings.append((label, path, 0, "올리면 안 되는 파일", path.rsplit("/", 1)[-1]))
            continue
        if line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            lineno = int(m.group(1)) if m else 0
            continue
        if path is None:
            continue
        if line.startswith("+"):
            for name, shown in scan_line(line[1:], *ctx):
                findings.append((label, path, lineno, name, shown))
            lineno += 1


def scan_commits(revlist_args, findings, ctx):
    shas = git("rev-list", *revlist_args).split()
    for sha in shas:
        short = sha[:7]
        meta = git("show", "-s", "--format=%ae%n%ce%n%B", sha)
        author, committer, *msg = meta.splitlines()
        for who, addr in (("작성자", author), ("커미터", committer)):
            if not any(a.search(addr) for a in ctx[2]):
                findings.append((short, f"(커밋 {who})", 0, "커밋에 박힌 이메일", mask(addr)))
        for i, mline in enumerate(msg, 1):
            for name, shown in scan_line(mline, *ctx):
                findings.append((short, "(커밋 메시지)", i, name, shown))
        patch = git("show", "--format=", "-U0", "--no-color", "--no-ext-diff", "--binary", sha)
        scan_patch(patch, short, findings, ctx)


def report(findings):
    findings = list(dict.fromkeys(findings))  # 같은 항목이 두 경로로 잡힌 경우 한 번만
    if not findings:
        print("[privacy] 개인정보·비밀값 없음")
        return 0
    print("[privacy] 막음: 아래 항목을 지우거나 .env/개인 설정으로 옮긴 뒤 다시 시도하세요.")
    for label, path, lineno, name, shown in findings:
        where = f"{path}:{lineno}" if lineno else path
        print(f"  - [{label}] {where}  {name}: {shown}")
    print("  정말 공개해도 되는 값이면 그 줄에 'privacy-allow' 주석을 달거나 personal.txt에 allow: 규칙을 추가하세요.")
    return 1


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    mode = sys.argv[1]
    ctx = load_personal()
    findings = []

    if mode == "add-secret":
        os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
        value = getpass.getpass("등록할 값(화면에 안 보임): ")
        if not value:
            return 1
        with open(CONFIG, "a", encoding="utf-8") as f:
            f.write("sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest() + "\n")
        print("[privacy] 해시로 등록했습니다(원래 값은 저장하지 않음).")
        return 0

    if mode == "staged":
        names = git("diff", "--cached", "--name-only", "--diff-filter=ACMR").splitlines()
        for n in names:
            if BLOCKED_FILES.search(n):
                findings.append(("staged", n, 0, "올리면 안 되는 파일", n.rsplit("/", 1)[-1]))
        patch = git("diff", "--cached", "-U0", "--no-color", "--no-ext-diff")
        scan_patch(patch, "staged", findings, ctx)
        # 이번 커밋에 찍힐 작성자 이메일
        email = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True).stdout.strip()
        if email and not any(a.search(email) for a in ctx[2]):
            findings.append(("staged", "(git config user.email)", 0, "커밋에 박힐 이메일", mask(email)))
    elif mode == "push":
        for raw in sys.stdin.read().splitlines():
            parts = raw.split()
            if len(parts) != 4:
                continue
            _local_ref, local_sha, _remote_ref, remote_sha = parts
            if local_sha == ZERO:  # 원격 브랜치 삭제
                continue
            if remote_sha == ZERO:
                scan_commits([local_sha, "--not", "--remotes"], findings, ctx)
            else:
                scan_commits([f"{remote_sha}..{local_sha}"], findings, ctx)
    elif mode == "range":
        scan_commits([sys.argv[2]], findings, ctx)
    elif mode == "tree":
        rev = sys.argv[2] if len(sys.argv) > 2 else "HEAD"
        for path in git("ls-tree", "-r", "--name-only", rev).splitlines():
            if BLOCKED_FILES.search(path):
                findings.append((rev, path, 0, "올리면 안 되는 파일", path.rsplit("/", 1)[-1]))
                continue
            blob = subprocess.run(["git", "show", f"{rev}:{path}"], capture_output=True).stdout
            if b"\0" in blob[:8000]:
                continue  # 바이너리
            for i, line in enumerate(blob.decode("utf-8", "replace").splitlines(), 1):
                if len(line) > 5000:
                    continue  # base64 이미지 등 한 줄짜리 거대 데이터
                for name, shown in scan_line(line, *ctx):
                    findings.append((rev, path, i, name, shown))
    else:
        print(__doc__)
        return 2
    return report(findings)


if __name__ == "__main__":
    sys.exit(main())
