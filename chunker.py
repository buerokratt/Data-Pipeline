import re
from logger_config import get_logger
from document_models import Chunk

CHUNK_SIZE = 2500
MAX_TABLE_ROWS_PER_CHUNK = 6

TABLE_PATTERN = re.compile(r"\[TABLE_ROW\s+\d+\]\s*(.*)")

logger = get_logger(__name__)


def estimate_tokens(text: str) -> int:
    # 1 token ≈ 4 chars
    return len(text) // 4


def section_has_heading(section):
    return bool(section.heading and section.heading.strip())


def log_large_chunks(chunks, limit_tokens=8000):
    for i, chunk in enumerate(chunks):
        tokens = estimate_tokens(chunk.content)

        if tokens > limit_tokens:
            logger.warning(
                "Large chunk detected | index=%s | tokens≈%s | heading=%s", i, tokens, chunk.section_heading,
            )


def split_content(text):
    lines = text.splitlines()

    table_rows = []
    normal_lines = []

    for line in lines:
        match = TABLE_PATTERN.match(line)

        if match:
            table_rows.append(line)
        else:
            normal_lines.append(line)

    return "\n".join(normal_lines).strip(), table_rows


def chunk_text(text: str):
    if not text:
        return []

    lines = text.split("\n")

    chunks = []
    current = []
    size = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if size + len(line) > CHUNK_SIZE:
            chunks.append("\n".join(current))
            current = [line]
            size = len(line)
        else:
            current.append(line)
            size += len(line)

    if current:
        chunks.append("\n".join(current))

    return chunks


def chunk_article(parsed_doc):
    chunks = []
    idx = 0

    for section in parsed_doc.sections:
        text = section.content.strip()
        if not text:
            continue

        normal_text, table_rows = split_content(text)

        # normal text chunks
        if section_has_heading(section):
            text_source = normal_text
        else:
            text_source = text

        for chunk in chunk_text(text_source):
            chunk_id = f"{parsed_doc.page_id}#{idx}"
            chunks.append(
                Chunk(
                    chunk_index=idx,
                    chunk_id=chunk_id,
                    section_heading=section.heading,
                    content=chunk,
                )
            )
            idx += 1

        # table row chunks
        for i in range(0, len(table_rows), MAX_TABLE_ROWS_PER_CHUNK):

            batch = table_rows[i : i + MAX_TABLE_ROWS_PER_CHUNK]
            chunk_id = f"{parsed_doc.page_id}#{idx}"

            chunks.append(
                Chunk(
                    chunk_index=idx,
                    chunk_id=chunk_id,
                    section_heading=section.heading,
                    content="\n".join(batch),
                )
            )
            idx += 1

    log_large_chunks(chunks)

    return chunks
