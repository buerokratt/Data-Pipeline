import json
from urllib.parse import quote
from bs4 import BeautifulSoup, Tag, Comment, NavigableString
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_text_splitters.html import HTMLSemanticPreservingSplitter
import os
import re
from config.app_config import Config

from logger_config import get_logger
logger = get_logger(__name__)

# Define directories
RAW_DIR = "raw_data"
PARSE_DIR = "parsed_data"

CHUNK_SIZE = 1900
CHUNK_OVERLAP = 100

PORTAL_URL = Config.PORTAL_URL


def _open_html(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            return BeautifulSoup(file, "html.parser")
    except Exception as e:
        print(f"Error opening/parsing HTML file {filepath}: {e}")
        return None


def clean_text(string_text):
    string_text = string_text.replace("\xa0", " ")
    string_text = string_text.replace("\u200b", "")
    string_text = re.sub(r"[ \t]+", " ", string_text)
    string_text = re.sub(r"\n{3,}", "\n\n", string_text)
    # string_text = re.sub(r"\s+", " ", string_text)
    return string_text.strip()


def extract_metadata(soup):  
    title = soup.title.string if soup.title else ""  
    description_tag = soup.find("meta", attrs={"name": "description"})  
    description = description_tag["content"] if description_tag and "content" in description_tag.attrs else "No Description"
    return title, description


def encode_url(url: str) -> str:
    """
    Properly encode only the path part of the URL.
    """
    if not url:
        return url

    parts = url.split("://", 1)
    if len(parts) != 2:
        return quote(url, safe="/:?=&")

    scheme, rest = parts

    return f"{scheme}://{quote(rest, safe='/:?=&')}"


def preserve_hyperlinks(soup):
    """
    Convert <a> tags to 'text (url)' in-place before splitting, ignoring local anchors.
    """
    for a_tag in soup.find_all("a"):
        href = a_tag.get("href", "").strip()
        if href.startswith("#accordion--"):
            a_tag.replace_with(a_tag.get_text(strip=True))
            continue
        link_text = a_tag.get_text(strip=True)
        if link_text:
            a_tag.replace_with(f"{link_text} ({href})")
        else:
            a_tag.decompose()
    return soup


def inject_image_placeholders(soup):
    """
    Replace all <img> tags in the full document with placeholders and return a mapping {placeholder: url}
    """
    image_map = {}
    counter = 1

    for img in soup.find_all("img"):
        src = (
            img.get("src")
            or img.get("data-src")
            or img.get("data-original")
            or img.get("data-lazy-src")
        )

        if not src:
            img.decompose()
            continue

        if src.startswith("/"):
            src = PORTAL_URL + src
        src = encode_url(src)

        # IMAGE REPLACEMENT
        # placeholder = f"[IMAGE_{counter}]"

        # IMAGE FULL URLS
        # placeholder = f"[{src}]"

        # REMOVE IMAGES
        placeholder = ""

        image_map[placeholder] = src

        img.replace_with(placeholder)
        counter += 1

    return image_map


def extract_cell_text_with_links(cell: Tag) -> str:
    """
    Extract text from a table cell, preserving hyperlinks as 'text (url)'.
    """
    parts = []

    for child in cell.descendants:
        if isinstance(child, Tag) and child.name == "a":
            link_text = clean_text(child.get_text(" ", strip=True))
            href = child.get("href", "").strip()
            if link_text:
                parts.append(f"{link_text} ({href})")
        
        elif isinstance(child, NavigableString):
            if any(
                isinstance(parent, Tag) and parent.name == "a"
                for parent in child.parents
            ):
                continue
            
            text = clean_text(str(child))
            if text:
                parts.append(text)

    final = " ".join(parts)
    final = re.sub(r"\s+", " ", final)
    return final.strip()


def table_to_markdown(table_tag):
    """
    Convert a BeautifulSoup <table> tag into a Markdown table string, preserving hyperlinks inside cells.
    """
    rows = []

    for row in table_tag.find_all("tr"):
        cells = []
        for cell in row.find_all(["th", "td"]):
            text = extract_cell_text_with_links(cell)
            if text:
                cells.append(text)
            else:
                cells.append("")
        if cells:
            rows.append(cells)

    if not rows:
        return ""

    first_row = table_tag.find("tr")
    header_cells = first_row.find_all("th")

    if header_cells:
        header = rows[0]
        body = rows[1:]

        md = "| " + " | ".join(header) + " |\n"
        md += "| " + " | ".join(["---"] * len(header)) + " |\n"

        for r in body:
            md += "| " + " | ".join(r) + " |\n"

        return md.strip()

    # No header
    md = ""
    for r in rows:
        md += "| " + " | ".join(r) + " |\n"

    return md.strip()


def headings_to_markdown(soup):
    for h2 in soup.find_all("h2"):
        text = clean_text(h2.get_text())
        h2.replace_with(NavigableString(f"__DNL__## {text}__NL__"))
    for h3 in soup.find_all("h3"):
        text = clean_text(h3.get_text())
        h3.replace_with(NavigableString(f"__DNL__### {text}__NL__"))
    return soup


def find_parent_accordion_title(card: Tag) -> str | None:
    """
    Walk up the DOM to find a parent element whose id starts with 'accordion-title'
    """
    parent = card.parent
    while parent and isinstance(parent, Tag):
        parent_id = parent.get("id", "")
        if parent_id.startswith("accordion-title"):
            return clean_text(parent.get_text(" ", strip=True))
        parent = parent.parent
    return None


def split_large_text_with_title(
    text: str,
    title_prefix: str | None,
    chunk_size: int,
    chunk_overlap: int
) -> list[str]:
    """
    Split long text at word boundaries and prefix each chunk with title_prefix.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " "]
    )

    chunks = splitter.split_text(text)

    if title_prefix:
        chunks = [f"[Section: {title_prefix}]\n{c}" for c in chunks]

    return chunks


def replace_tables_with_markdown(soup):
    """
    Replace each <table> with a markdown block placeholder so it stays in correct position.
    """
    table_map = {}
    counter = 1

    for table in soup.find_all("table"):
        try:
            md = table_to_markdown(table)

            if not md.strip():
                table.decompose()
                continue

            placeholder = f"[TABLE_{counter}]"
            table_map[placeholder] = md

            table.replace_with(placeholder)
            counter += 1

        except Exception as e:
            print(f"Table conversion failed: {e}")
            table.decompose()

    return table_map


def extract_and_remove_tables(soup):
    """
    Extract all tables as markdown strings and remove them from the soup.
    """
    markdown_tables = []

    for table in list(soup.find_all("table")):
        try:
            md = table_to_markdown(table)
            if md.strip():
                markdown_tables.append(md)
        except Exception as e:
            print(f"Warning: failed converting table to markdown: {e}")
        
        try:
            table.decompose()
        except:
            pass

    return markdown_tables


def extract_and_remove_cards(soup):
    """
    Extract all cards, including nested cards. Nested cards inherit the nearest parent accordion title.
    Oversized cards are chunked with overlap.
    """
    extracted_chunks = []

    cards = soup.find_all(class_="card")
    cards = sorted(cards, key=lambda c: len(list(c.parents)), reverse=True)

    for card in list(cards):
        try:
            parent_title = find_parent_accordion_title(card)

            card_html = str(card)
            card_text = html_chunk_to_text(card_html)
            card_text = clean_text(card_text)

            if not card_text:
                card.decompose()
                continue

            if len(card_text) > CHUNK_SIZE * 2:
                chunks = split_large_text_with_title(
                    card_text,
                    parent_title,
                    CHUNK_SIZE,
                    CHUNK_OVERLAP
                )
                extracted_chunks.extend(chunks)

            else:
                if parent_title:
                    card_text = f"[Section: {parent_title}]\n{card_text}"
                extracted_chunks.append(card_text)

        except Exception as e:
            print(f"Warning: failed extracting card content: {e}")

        # Remove card
        try:
            card.decompose()
        except:
            pass

    return extracted_chunks


def pre_clean_html(soup):
    if not soup:
        return soup

    # Remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Remove unwanted block tags
    for tag in list(soup.find_all(["nav", "header", "aside", "footer", "menu", "script", "style", "noscript", "title"])):
        try:
            tag.decompose()
        except:
            pass

    testid_denylist = {
        "juhendid-page-breadcrumbs",
        "juhendid-page-title"
    }
        
    # Remove breadcrumbs by data-testid attribute
    for tag in soup.find_all(attrs={"data-testid": True}):
        if tag.get("data-testid") in testid_denylist:
            try:
                tag.decompose()
            except:
                pass

    # Remove elements with denylist classes
    deny_tokens = {
        "guide-search-section",
        "guide-folders-card",
        "toc-content-no-border",
        "sr-only",
        "hidden",
        "modal",
        "no-print",
        "adf-expand-chevron"
    }
    for tag in list(soup.find_all(class_=True)):
        try:
            classes = tag.get("class") or []
            if isinstance(classes, str):
                classes = classes.split()
            if any(tok in classes for tok in deny_tokens):
                if tag.name == "a" and tag.get("href"):
                    continue

                tag.decompose()
        except:
            pass

    # Remove elements with display: none
    for tag in list(soup.find_all(style=True)):
        if tag is None or not isinstance(tag, Tag):
            continue
        try:
            style_val = tag.attrs.get("style", "")
        except:
            continue
        if not style_val:
            continue
        style_norm = re.sub(r"\s+", "", style_val.lower())
        if "display:none" in style_norm or re.search(r"display\s*:\s*none", style_val, flags=re.I):
            try:
                tag.decompose()
            except:
                pass

    return soup


def html_chunk_to_text(html_chunk: str) -> str:
    """
    Convert HTML chunk into text and replace images with placeholders
    """
    soup = BeautifulSoup(html_chunk, "html.parser")

    images = []
    image_counter = 1

    for img in soup.find_all("img"):
        src = (
            img.get("src")
            or img.get("data-src")
            or img.get("data-original")
            or img.get("data-lazy-src")
        )

        if src:
            if src.startswith("/"):
                src = PORTAL_URL + src
            src = encode_url(src)

            placeholder = f"[imgurl_{image_counter}]"
            images.append(src)
            image_counter += 1

            img.replace_with(placeholder)
        else:
            img.decompose()

    structured_output = []

    formatted_text = "\n".join(structured_output)

    if not formatted_text:
        formatted_text = soup.get_text(separator="\n", strip=True)

    return formatted_text, images


def create_json_with_text_from_html(html_file, output_file, source_url, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, min_chunk_length=40):
    soup = _open_html(html_file)
    title, description = extract_metadata(soup)
    full_url = source_url

    image_map = inject_image_placeholders(soup)
    table_map = replace_tables_with_markdown(soup)

    soup = pre_clean_html(soup)

    markdown_cards = extract_and_remove_cards(soup)
    soup = preserve_hyperlinks(soup)
    soup = headings_to_markdown(soup)

    json_data = []

    def extract_images_from_text(text, image_map):
        found_images = []

        for placeholder, url in image_map.items():
            if placeholder in text:
                found_images.append(url)

        return found_images
    
    def inject_tables_back(text, table_map):
        """
        Replace table placeholders with actual markdown.
        """
        for placeholder, table_md in table_map.items():
            if placeholder in text:
                text = text.replace(
                    placeholder,
                    f"\n\n{table_md}\n\n"
                )
        return text
    
    def split_oversized_chunk(chunk, chunk_size):
        """
        Second-pass splitter for chunks that became too large after table injection.
        Splits ONLY on headings (##, ###), never inside tables.
        """
        if len(chunk) <= chunk_size * 3:
            return [chunk]
        
        if len(chunk) > chunk_size * 6:
            logger.warning(f"Extremely large chunk detected ({len(chunk)} chars).")

        # Split on headings
        parts = re.split(r'(## |### )', chunk)

        # Rebuild chunks with headings preserved
        rebuilt = []
        current = ""

        for part in parts:
            if part.startswith("## ") or part.startswith("### "):
                if current:
                    rebuilt.append(current)
                current = part
            else:
                current += part

        if current:
            rebuilt.append(current)

        return rebuilt
    
    def preserve_lists(soup):
        for ol in soup.find_all("ol"):
            items = []

            for idx, li in enumerate(ol.find_all("li", recursive=False), start=1):
                text = clean_text(li.get_text(" ", strip=True))
                items.append(f"__NL__{idx}. {text}")

            ol.replace_with(" ".join(items))

        for ul in soup.find_all("ul"):
            items = []

            for li in ul.find_all("li", recursive=False):
                text = clean_text(li.get_text(" ", strip=True))
                items.append(f"__NL__- {text}")

            ul.replace_with(" ".join(items))

        return soup

    # Add cards as standalone chunks
    for card_text in markdown_cards:
        json_data.append({
            "content": {
                "chunk": card_text,
                # "imgurl": images,
                "imgurl": "",
                "title": title,
                "description": description,
                "source_url": full_url
            }
        })

    soup = preserve_lists(soup)

    remaining_html = str(soup)

    sem_splitter = HTMLSemanticPreservingSplitter(
        headers_to_split_on=[
            ("h1","h1"),
            ("h2","h2"),
            ("h3","h3")
        ],
        separators=["\n\n", "\n"],
        denylist_tags=["nav", "header", "aside", "footer", "menu", "script", "style", "title"],
        max_chunk_size=chunk_size * 3
    )
    semantic_blocks = sem_splitter.split_text(remaining_html)

    rec_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=[
            "##",
            "###",
            "\n\n[TABLE_",
            "\n\n",
            "\n",
            " "
        ]
    )

    all_pairs = []

    for block in semantic_blocks:
        sub_chunks = rec_splitter.split_text(block.page_content)

        for c in sub_chunks:
            text, images = html_chunk_to_text(c)
            text = (
                text
                .replace("__DNL__", "\n\n")
                .replace("__NL__", "\n")
            )
            text = clean_text(text)

            images = extract_images_from_text(text, image_map)
            text = inject_tables_back(text, table_map)

            if text.strip():
                all_pairs.append((text, images))

    for text, images in all_pairs:
        split_chunks = split_oversized_chunk(text, chunk_size)
        for chunk in split_chunks:
            json_data.append({
                "content": {
                    "chunk": chunk,
                    # "imgurl": images,
                    "imgurl": "",
                    "title": title,
                    "description": description,
                    "source_url": full_url
                }
            })

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)

    print(f"JSON file '{output_file}' created successfully with {len(json_data)} chunks.")


def chunk_and_parse():
    os.makedirs(PARSE_DIR, exist_ok=True)

    for root, _, files in os.walk(RAW_DIR):
        for file in files:
            if file.endswith(".html"):
                raw_file_path = os.path.join(root, file)
                parse_file_path = os.path.join(PARSE_DIR, file.replace(".html", ".json"))
                try:
                    filename = file.replace(".html", "")
                    source_url = filename.replace("___", "://").replace("__", "/")

                    create_json_with_text_from_html(raw_file_path, parse_file_path, source_url)
                except Exception as e:
                    print(f"Failed to process {raw_file_path}: {e}")

if __name__ == "__main__":
    chunk_and_parse()