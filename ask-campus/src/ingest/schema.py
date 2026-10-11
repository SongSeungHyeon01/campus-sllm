"""Chunk record shared by every source (계획서 2-나 문서 청크 스키마)."""
import textwrap
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

# Korean text runs roughly 1.5–2 chars per token, so 1000 chars stays inside the
# 300~800 token chunk size set in the plan.
MAX_CHARS = 1000


def now_kst() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


@dataclass
class Chunk:
    chunk_id: str
    category: str  # 학사정보 / 통학버스 / 동아리 / 캠퍼스시설 / 일반공지 / 교외활동
    title: str
    content: str
    source_url: str
    collected_at: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def pack(header: str, lines: list[str], max_chars: int = MAX_CHARS) -> list[str]:
    """Group lines into chunks of at most max_chars, repeating the header in each.

    The header carries the context (campus, table name, notice title) so a chunk
    retrieved on its own still says what it is about.
    """
    budget = max(200, max_chars - len(header) - 1)
    pieces = []
    for line in lines:
        pieces.extend(textwrap.wrap(line, budget) if len(line) > budget else [line])

    chunks, current, size = [], [], 0
    for piece in pieces:
        if current and size + len(piece) + 1 > budget:
            chunks.append(current)
            current, size = [], 0
        current.append(piece)
        size += len(piece) + 1
    if current:
        chunks.append(current)
    return ["\n".join([header, *c]) if header else "\n".join(c) for c in chunks]
