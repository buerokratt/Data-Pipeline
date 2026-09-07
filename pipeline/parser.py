from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, NavigableString


_HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")


def parse_document(
    payload: dict[str, Any],
    *,
    chunk_size: int,
    chunk_overlap: int,
    source_url: str,
) -> dict[str, Any]:
    document_id = payload["documentUuid"]
    html = payload.get("htmlContent", "")

    if not html:
        raise ValueError(f"Document {document_id} has empty htmlContent")

    soup = BeautifulSoup(html, "html.parser")
    title = extract_title(soup)
    sections = extract_sections(soup)

    chunks: list[dict[str, Any]] = []
    for section in sections:
        for text in chunk_section(section["text"], chunk_size, chunk_overlap):
            chunks.append(
                {
                    "chunk_id": f"{document_id}#{len(chunks)}",
                    "title": title,
                    "section_heading": section["heading"],
                    "chunk": text,
                    "source_url": source_url,
                }
            )

    return {
        "document_id": document_id,
        "title": title,
        "target_market": payload.get("countryCode") or "GLOBAL",
        "deleted": False,
        "deleted_at": None,
        "chunks": chunks,
        "_pipeline": {
            "html_content_sha256": payload.get("contentSha256"),
            "html_file_name": payload.get("metadata", {}).get("htmlFileName", ""),
        },
    }


def make_deleted_document(
    *,
    document_id: str,
    title: str = "",
    country_code: str = "",
    deleted_at: str | None = None,
) -> dict[str, Any]:
    return {
        "document_id": document_id,
        "title": title,
        "target_market": country_code,
        "deleted": True,
        "deleted_at": deleted_at,
        "chunks": [],
    }


def extract_title(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1")
    if h1:
        return clean_text(h1.get_text(" ", strip=True))
    title = soup.find("title")
    return clean_text(title.get_text(" ", strip=True)) if title else ""


def extract_sections(soup: BeautifulSoup) -> list[dict[str, str | None]]:
    for node in soup.select("nav.document-table-of-contents, header.document-header"):
        node.decompose()

    main = soup.select_one("main.document-content")
    if not main:
        return []

    sections: list[dict[str, str | None]] = []

    for section in main.find_all("section", recursive=True):
        heading_node = section.find(list(_HEADING_TAGS))
        heading = clean_text(heading_node.get_text(" ", strip=True)) if heading_node else None
        text = extract_clean_text(section)

        if text:
            sections.append(
                {
                    "heading": heading,
                    "text": text,
                    "page": section.get("data-page-number"),
                }
            )

    return sections


def extract_clean_text(section: Any) -> str:
    """
    Render section HTML as MD

    Headings get prepended with '#' and list items become '- ' or numbered lists.
    Paragraphs marked 'empty-section' are removed.
    """
    soup = BeautifulSoup(str(section), "html.parser")

    for nav in soup.select("nav.document-table-of-contents"):
        nav.decompose()

    for paragraph in soup.select("p.empty-section"):
        paragraph.decompose()

    # Convert headings to markdown
    for heading in soup.find_all(list(_HEADING_TAGS)):
        level = int(heading.name[1])
        heading_text = clean_inline_text(heading.get_text(" ", strip=True))
        heading.replace_with(NavigableString(f"\n{'#' * level} {heading_text}\n"))

    # Convert unordered/ordered list items
    for ul in soup.find_all("ul"):
        for li in ul.find_all("li", recursive=False):
            li.insert_before(NavigableString("\n- "))
            li.append(NavigableString("\n"))
        ul.unwrap()

    for ol in soup.find_all("ol"):
        for i, li in enumerate(ol.find_all("li", recursive=False), start=1):
            li.insert_before(NavigableString(f"\n{i}. "))
            li.append(NavigableString("\n"))
        ol.unwrap()

    # Give paragraphs and divs line boundaries
    for tag in soup.find_all(["p", "div"]):
        tag.insert_before(NavigableString("\n"))
        tag.append(NavigableString("\n"))

    text = soup.get_text(separator="")

    return normalize_markdown_whitespace(text)


def chunk_section(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and < chunk_size")

    sentences = split_sentences(text)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if len(sentence) > chunk_size:
            if current:
                chunks.append(current.strip())
                current = ""

            for start in range(0, len(sentence), chunk_size):
                chunks.append(sentence[start : start + chunk_size].strip())
            continue

        candidate = f"{current} {sentence}".strip()

        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current.strip())
            current = overlap_text(current, chunk_overlap)

        candidate = f"{current} {sentence}".strip()
        
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current.strip())
            current = sentence

    if current.strip():
        chunks.append(current.strip())

    return chunks


def overlap_text(text: str, overlap_chars: int) -> str:
    if not text or overlap_chars == 0:
        return ""
    if len(text) <= overlap_chars:
        return text

    start = len(text) - overlap_chars
    while start < len(text) and not text[start].isspace():
        start += 1

    return text[start:].strip()


def split_sentences(text: str) -> list[str]:
    # Keep markdown heading/list lines intact as individual units, then split ordinary text into sentences
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    sentences: list[str] = []
    for line in lines:
        if line.startswith("#") or line.startswith("- ") or re.match(r"^\d+\. ", line):
            sentences.append(line)
        else:
            sentences.extend(re.split(r"(?<=[.!?])\s+", line))

    return [s.strip() for s in sentences if s.strip()]


def normalize_markdown_whitespace(text: str) -> str:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if line:
            lines.append(line)
            
    return "\n".join(lines)


def clean_inline_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def clean_text(text: str) -> str:
    return clean_inline_text(text)
