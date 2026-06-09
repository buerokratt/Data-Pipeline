import json
import os
import re

from collections import defaultdict
from config.app_config import Config
from document_models import ParsedDocument, Section
from logger_config import get_logger

PORTAL_URL = Config.PORTAL_URL

logger = get_logger(__name__)

KNOWN_NODE_TYPES = {
    "text",
    "paragraph",
    "heading",
    "bulletList",
    "orderedList",
    "listItem",
    "hardBreak",
    "media",
    "mediaSingle",
    "table",
    "tableRow",
    "tableCell",
    "expand",
    "panel",
    "tableHeader",
    "mediaInline",
    "blockquote",
    "nestedExpand",
}

UNKNOWN_NODE_TYPES = defaultdict(int)


def log_unknown_nodes():
    if not UNKNOWN_NODE_TYPES:
        logger.info("No unknown ADF node types found")
        return

    logger.warning("Unknown ADF node types encountered:")

    for k, v in sorted(UNKNOWN_NODE_TYPES.items(), key=lambda x: -x[1]):
        logger.warning("  %s -> %s", k, v)


def build_attachment_map(attachments):
    return {
        att["fileId"]: {
            "title": att.get("title"),
            "media_type": att.get("mediaType"),
            "download_url": build_attachment_url(att["fileId"], att["title"]),
        }
        for att in attachments
        if att.get("fileId")
    }


def build_attachment_url(file_id, title):
    return f"{Config.PORTAL_URL}/api/v1/attachments/{file_id}/{title}"


def detect_table_type(table_node):
    first_row = table_node.get("content", [None])[0]
    if not first_row:
        return "unknown"

    first_cell = first_row.get("content", [None])[0]
    if not first_cell:
        return "unknown"

    cell_type = first_cell.get("type")

    if cell_type == "tableHeader":
        return "header_table"

    if cell_type == "tableCell":
        return "key_value_table"

    return "mixed"


def normalize_cell_text(node, attachment_map=None):
    text = extract_text(node, attachment_map).strip()

    # collapse whitespace / newlines
    text = " ".join(text.split())

    return text


def join_children(node, attachment_map=None, indent=0):
    return "".join(
        extract_text(child, attachment_map, indent) for child in node.get("content", [])
    )


def extract_text(node, attachment_map=None, indent=0):
    node_type = node.get("type", "UNKNOWN")

    if node_type not in KNOWN_NODE_TYPES:
        UNKNOWN_NODE_TYPES[node_type] = UNKNOWN_NODE_TYPES.get(node_type, 0) + 1

    # text nodes
    if node_type == "text":
        text = node.get("text", "")
        marks = node.get("marks", [])

        for mark in marks:
            if mark.get("type") == "link":
                href = mark.get("attrs", {}).get("href")

                if href:
                    text = f"{text} ({href})"

        return text

    # paragraph nodes
    if node_type == "paragraph":

        return (
            "".join(
                extract_text(child, attachment_map, indent)
                for child in node.get("content", [])
            )
            + "\n"
        )

    # newlines
    if node_type == "hardBreak":
        return "\n"

    # bulleted lists
    if node_type == "bulletList":
        lines = []

        for item in node.get("content", []):
            text = extract_text(item, attachment_map, indent + 1)

            lines.append("  " * indent + f"- {text.strip()}")

        return "\n".join(lines) + "\n"

    # ordered lists
    if node_type == "orderedList":
        lines = []

        for idx, item in enumerate(node.get("content", []), start=1):
            text = extract_text(item, attachment_map, indent + 1)

            lines.append("  " * indent + f"{idx}. {text.strip()}")

        return "\n".join(lines) + "\n"

    # list items
    if node_type == "listItem":

        return "".join(
            extract_text(child, attachment_map, indent)
            for child in node.get("content", [])
        )

    # tables
    if node_type == "table":
        rows = node.get("content", [])

        if not rows:
            return ""

        table_type = detect_table_type(node)
        output_rows = []

        # table with header
        if table_type == "header_table":
            header_cells = rows[0].get("content", [])

            headers = [normalize_cell_text(cell, attachment_map) for cell in header_cells]

            for r_idx, row in enumerate(rows[1:], start=1):
                row_cells = row.get("content", [])

                values = [normalize_cell_text(cell, attachment_map) for cell in row_cells]

                row_pairs = [f"{h}: {v}" for h, v in zip(headers, values)]

                output_rows.append(f"[TABLE_ROW {r_idx}] " + " | ".join(row_pairs))

        # key-value table (no header)
        elif table_type == "key_value_table":
            for r_idx, row in enumerate(rows, start=1):
                cells = row.get("content", [])

                values = [normalize_cell_text(cell, attachment_map) for cell in cells]

                if len(values) >= 2:
                    output_rows.append(f"[TABLE_ROW {r_idx}] {values[0]}: {values[1]}")
                else:
                    output_rows.append(f"[TABLE_ROW {r_idx}] {' '.join(values)}")

        # fallback
        else:
            for r_idx, row in enumerate(rows, start=1):
                cells = row.get("content", [])
                values = [normalize_cell_text(cell, attachment_map) for cell in cells]

                output_rows.append(f"[TABLE_ROW {r_idx}] " + " | ".join(values))

        return "\n".join(output_rows) + "\n"

    # images (placeholder)
    if node_type == "media":
        alt = node.get("attrs", {}).get("alt", "")

        if alt:
            return f"[IMAGE: {alt}]"

        return "[IMAGE]"

    # images (link)
    if node_type == "mediaSingle":

        return (
            "".join(
                extract_text(child, attachment_map, indent)
                for child in node.get("content", [])
            )
            + "\n"
        )

    # inline files (link)
    if node_type == "mediaInline":
        attrs = node.get("attrs", {})
        file_id = attrs.get("id")

        if attachment_map and file_id in attachment_map:
            att = attachment_map[file_id]
            title = att.get("title", "unknown_file")
            download_url = att["download_url"]

            return f"{title} ({download_url})"

        return "[ATTACHMENT]"

    # panels
    if node_type == "panel":
        text = join_children(node, indent).strip()

        if not text:
            return ""

        return f"\n[PANEL]\n{text}\n[/PANEL]\n"

    # blockquotes
    if node_type == "blockquote":
        text = join_children(node, indent).strip()

        if not text:
            return ""

        return f"\n> {text}\n"

    # expands
    if node_type == "expand":
        title = node.get("attrs", {}).get("title", "")
        body = join_children(node, indent).strip()

        if title:
            return f"\n[EXPAND: {title}]\n{body}\n[/EXPAND]\n"

        return f"\n[EXPAND]\n{body}\n[/EXPAND]\n"

    # nested expands
    if node_type == "nestedExpand":
        title = node.get("attrs", {}).get("title", "")
        body = join_children(node, indent).strip()

        if title:
            return f"\n[NESTED_EXPAND: {title}]\n{body}\n[/NESTED_EXPAND]\n"

        return f"\n[NESTED_EXPAND]\n{body}\n[/NESTED_EXPAND]\n"

    # empty paragraphs
    if node_type == "paragraph":
        content = "".join(
            extract_text(child, attachment_map, indent)
            for child in node.get("content", [])
        )

        return content + "\n" if content.strip() else ""

    return "".join(
        extract_text(child, attachment_map, indent) for child in node.get("content", [])
    )


def flatten_content(nodes, attachment_map=None, section_heading=None):
    parts = []

    for node in nodes:
        text = extract_text(node, attachment_map).strip()

        if not text:
            continue

        if text.startswith("[TABLE_ROW"):
            text = f"[SECTION: {section_heading}]\n" + text

        parts.append(text)

    return "\n".join(parts)


def parse_article(article: dict) -> ParsedDocument:
    attachment_map = build_attachment_map(article.get("attachments", []))
    content_nodes = article["content"]["content"]

    sections = []
    current_content = []

    current_heading = ""
    current_level = None

    for node in content_nodes:
        node_type = node.get("type")

        if node_type == "heading":

            # flush previous section
            if current_content:
                sections.append(
                    Section(
                        heading=current_heading,
                        level=current_level,
                        content=flatten_content(
                            current_content, attachment_map, current_heading
                        ),
                    )
                )

            current_heading = extract_text(node, attachment_map).strip()
            current_level = node.get("attrs", {}).get("level")
            current_content = []

        else:
            current_content.append(node)

    # flush final section
    if current_content:
        sections.append(
            Section(
                heading=current_heading,
                level=current_level,
                content=flatten_content(
                    current_content, attachment_map, current_heading
                ),
            )
        )

    full_url = PORTAL_URL + "/juhendid/" + article["tenantId"] + "/" + article["pageId"]

    return ParsedDocument(
        page_id=article["pageId"],
        title=article["title"],
        source_url=full_url,
        sections=sections,
    )


def save_parsed_blob(blob_doc, output_dir=Config.PARSED_DATA):
    os.makedirs(output_dir, exist_ok=True)

    page_id = blob_doc["page_id"]

    title = blob_doc["title"]

    safe_title = re.sub(r'[<>:"/\\|?*;]', "", title.replace(" ", "_"))

    filename = f"{page_id}_{safe_title}.json"

    output_path = os.path.join(output_dir, filename)

    with open(output_path, "w", encoding="utf-8") as f:

        json.dump(blob_doc, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved parsed blob {filename} with {len(blob_doc['chunks'])} chunk(s)")
