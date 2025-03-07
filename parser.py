import json
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import re
from config.app_config import Config

from logger_config import get_logger
logger = get_logger(__name__)  

URL = Config.WEB_PAGE_URL

# Define directories
RAW_DIR = "raw_data"
PARSE_DIR = "parsed_data"


def _open_html(filepath):
    with open(filepath, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")
    return soup

def clean_text(string_text):
    # Remove <ul> and </ul> tags
    string_text = re.sub(r"</?ul>", "", string_text)

    # Remove <li> and </li> tags
    string_text = re.sub(r"</?li>", "", string_text)

    # Remove <p> and </p> tags
    string_text = re.sub(r"</?p>", "", string_text)

    # Remove <strong> and </strong> tags
    string_text = re.sub(r"</?strong>", "", string_text)

    # Remove <strong> and </strong> tags
    string_text = re.sub(r"\xa0", "", string_text)
    string_text = re.sub(r"<br/>", "", string_text)

    return string_text

def extract_metadata(soup):  
    """Extracts the title, description, and full URL from the HTML soup."""  
    title = soup.title.string if soup.title else "No Title"  
    description_tag = soup.find("meta", attrs={"name": "description"})  
    description = description_tag["content"] if description_tag and "content" in description_tag.attrs else "No Description"  
    url_tag = soup.find("meta", property="og:url")  
    full_url = url_tag["content"] if url_tag and "content" in url_tag.attrs else "No URL"  
    return title, description, full_url  

def extract_text_and_images(html_soup):  
    """Extracts raw text and image URLs from an HTML file."""  
    # Remove unwanted tags  
    for tag in html_soup.find_all(["nav", "header", "aside", "footer", "menu", "script", "style"]):  
        tag.decompose()  
  
    # Remove elements with specific class names  
    for tag in html_soup.find_all(class_="page-author-card-name"):  
        tag.decompose()  
  
    chunks = []
    current_chunk = {"chunk": "", "imgurl": []}

    for element in html_soup.find_all(["p", "ul", "ol", "h2", "h3", "li", "figure", "br", "img"]):
        if element.name == "figure":
            img_tag = element.find("img")
            if img_tag and "src" in img_tag.attrs:
                current_chunk["imgurl"].append(img_tag["src"])
        elif element.name == "img":
            if "src" in element.attrs:
                if element["src"] not in current_chunk["imgurl"]:
                    current_chunk["imgurl"].append(element["src"])
        else:
            for img_tag in element.find_all("img"):
                if "src" in img_tag.attrs:
                    current_chunk["imgurl"].append(img_tag["src"])
                img_tag.extract()  # Remove image from text
            text = str(element) if element.string == None else element.string
            if text:
                if len(current_chunk["chunk"]) > 0:
                    chunks.append(current_chunk)  # Store the previous chunk
                    current_chunk = {"chunk": "", "imgurl": []}  # Reset chunk
                current_chunk["chunk"] = text  # Start new chunk
    if current_chunk["chunk"]:  
        chunks.append(current_chunk)  # Add the last chunk

    return chunks
    
def create_json(html_file, output_file,chunk_size=1000, chunk_overlap=80):  
    """Extracts content, chunks text, and saves it in JSON format.
        Inputs : 
        - html_file :input .html file name
        - html_file :input output .json file.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        #separators=["\n\n", "\n", " ", ""],
    )
    logger.info(f"parsing and chunking file: {html_file}")
    soup = _open_html(html_file)  
    elements = extract_text_and_images(soup)
    title, description, full_url = extract_metadata(soup)
    json_data = []
    buffer = ""
    buffer_images = []
    for element in elements:
        element["chunk"] = clean_text(element["chunk"])
        buffer += element["chunk"]
        buffer_images.extend(element["imgurl"])
        buffer_images = list(dict.fromkeys(buffer_images))
        if len(buffer) >= chunk_size:
            chunks = text_splitter.split_text(buffer)
            for chunk in chunks: 
                json_data.append({  
                    "content": {  
                        "chunk": chunk,  
                        "imgurl": list(map(lambda x: URL + x, buffer_images)) ,
                        "title" : title,
                        "description" : description,
                        "source_url" : full_url
                    }  
                })
            buffer, buffer_images = "", []
    if buffer:  # Add remaining text
        #buffer_images = list(map(lambda x: URL + x, buffer_images)) 
        json_data.append({  
                    "content": {  
                        "chunk": buffer,  
                        "imgurl": list(map(lambda x: URL + x, buffer_images)) ,
                        "title" : title,
                        "description" : description,
                        "source_url" : full_url
                    }  
                })

    with open(output_file, "w", encoding="utf-8") as json_file:  
        json.dump(json_data, json_file, ensure_ascii=False, indent=4)  
      
    logger.info(f"JSON file '{output_file}' created successfully.")
#
def chunk_and_parse():
    os.makedirs(PARSE_DIR, exist_ok=True)
    for root, _, files in os.walk(RAW_DIR):
        for file in files:
            if file.endswith(".html"):
                raw_file_path = os.path.join(root, file)
                parse_file_path = os.path.join(PARSE_DIR, file.replace(".html", ".json"))
                create_json(raw_file_path, parse_file_path)
