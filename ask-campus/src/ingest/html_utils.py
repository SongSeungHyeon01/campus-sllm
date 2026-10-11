"""HTML helpers for u1.ac.kr pages: content area lookup and table flattening."""
import re

from bs4 import BeautifulSoup, Tag

_WS = re.compile(r"\s+")


def clean(text: str) -> str:
    return _WS.sub(" ", text).strip()


def soup_of(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def cms_content(html: str) -> Tag:
    """Every u1.ac.kr sub page puts its body inside #cms-content."""
    content = soup_of(html).select_one("#cms-content")
    if content is None:
        raise ValueError("#cms-content not found — page layout may have changed")
    return content


def page_title(html: str) -> str:
    """'영동캠퍼스 | 유원대학교' -> '영동캠퍼스'"""
    title = soup_of(html).title
    return clean(title.get_text()).split("|")[0].strip() if title else ""


def text_lines(tag: Tag) -> list[str]:
    """Visible text of a tag, one cleaned line per block, consecutive duplicates removed."""
    lines = []
    for raw in tag.get_text("\n").split("\n"):
        line = clean(raw)
        if line and (not lines or lines[-1] != line):
            lines.append(line)
    return lines


def _span(cell: Tag, attr: str) -> int:
    try:
        return max(1, int(cell.get(attr, 1)))
    except (TypeError, ValueError):
        return 1


def _expand(rows: list[Tag]) -> list[list[tuple[str, int, bool]]]:
    """Fill rowspan/colspan so every row has one entry per column.

    Each entry is (text, cell_id, is_header); cell_id lets callers tell a spanned
    copy apart from a new cell with the same text.
    """
    grid = []
    carry: dict[int, tuple[tuple[str, int, bool], int]] = {}
    for tr in rows:
        queue = tr.find_all(["th", "td"], recursive=False)
        row = []
        col = 0
        while queue or col in carry:
            if col in carry:
                entry, left = carry.pop(col)
                if left > 1:
                    carry[col] = (entry, left - 1)
                row.append(entry)
                col += 1
                continue
            cell = queue.pop(0)
            entry = (clean(cell.get_text(" ")), id(cell), cell.name == "th")
            rowspan = _span(cell, "rowspan")
            for _ in range(_span(cell, "colspan")):
                if rowspan > 1:
                    carry[col] = (entry, rowspan - 1)
                row.append(entry)
                col += 1
        grid.append(row)
    return grid


def table_records(table: Tag) -> list[list[tuple[str, str]]]:
    """Body rows of a table as [(column label, value), ...].

    Column labels join the header rows top to bottom ('등교' + '영동역' -> '등교 영동역').
    A body cell spanning several columns is emitted once with a 'first~last' label.
    """
    grid = _expand(table.find_all("tr"))
    thead = table.find("thead")
    if thead is not None:
        n_head = len(thead.find_all("tr"))
    else:
        n_head = 0
        while n_head < len(grid) and grid[n_head] and all(e[2] for e in grid[n_head]):
            n_head += 1
    head, body = grid[:n_head], grid[n_head:]

    width = max((len(r) for r in grid), default=0)
    labels = []
    for c in range(width):
        parts: list[str] = []
        for row in head:
            if c < len(row) and row[c][0] and (not parts or parts[-1] != row[c][0]):
                parts.append(row[c][0])
        labels.append(" ".join(parts))

    records = []
    for row in body:
        pairs = []
        c = 0
        while c < len(row):
            text, cell_id, _ = row[c]
            end = c
            while end + 1 < len(row) and row[end + 1][1] == cell_id:
                end += 1
            if text:
                label = labels[c] if c < len(labels) else ""
                if end > c and end < len(labels) and labels[end] != label:
                    label = f"{label}~{labels[end]}"
                pairs.append((label, text))
            c = end + 1
        if pairs:
            records.append(pairs)
    return records


def record_to_text(pairs: list[tuple[str, str]]) -> str:
    return " / ".join(f"{k}: {v}" if k and k != v else v for k, v in pairs)


def table_title(table: Tag) -> str:
    """Caption's <strong> (the short title), else the nearest heading above the table."""
    caption = table.find("caption")
    if caption is not None:
        strong = caption.find("strong")
        text = clean((strong or caption).get_text(" "))
        if text:
            return text
    heading = table.find_previous(["h4", "h5"])
    return clean(heading.get_text(" ")) if heading else ""
