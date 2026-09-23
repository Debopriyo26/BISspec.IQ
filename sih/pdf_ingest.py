import os
import re
import csv
import time

try:
    # pyrefly: ignore [missing-import]
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

PLACEHOLDER_TEXT = (
    "Standard specification text could not be automatically extracted from this PDF. "
    "This typically occurs with scanned documents, image-based PDFs, or encrypted files. "
    "Please refer to the physical document."
)


def extract_text_from_pdf(pdf_source):
    """
    Extracts raw text from a PDF file path or file stream using PyPDF2.
    Properly handles stream seeking to prevent empty reads and avoids binary gibberish.
    """
    # 1. Reset the stream: Ensure the cursor is at the beginning before PyPDF2 reads it
    if hasattr(pdf_source, 'seek'):
        pdf_source.seek(0)

    extracted_text = ""

    if PYPDF2_AVAILABLE:
        try:
            reader = PdfReader(pdf_source)
            text_pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_pages.append(text)
            if text_pages:
                extracted_text = " ".join(text_pages)
        except Exception as e:
            print(f"PyPDF2 extraction notice: {str(e)}")

    # 2. If extraction fails, or text is empty/has fewer than 10 word/alphanumeric characters, return clean placeholder
    # Using \w and Unicode letter check to fully support regional Indian languages (Hindi, Gujarati, Tamil, etc.)
    if not extracted_text or not extracted_text.strip() or len(re.findall(r'[\w\u0900-\u0D7F]', extracted_text)) < 10:
        return PLACEHOLDER_TEXT

    return extracted_text


def clean_extracted_text(raw_text):
    """
    Cleans raw PDF text for optimal TF-IDF vectorization and readable UI display.
    Preserves alphanumeric characters across English and regional Indian languages
    (Unicode blocks \u0900-\u0D7F for Devanagari, Bengali, Gujarati, Tamil, Telugu, etc.),
    removes redundant newlines, and standardizes spacing.
    """
    if not raw_text:
        return ""

    if raw_text == PLACEHOLDER_TEXT:
        return PLACEHOLDER_TEXT

    # Normalize newlines and tabs to space
    cleaned = re.sub(r'[\r\n\t]+', ' ', raw_text)
    # Strip out symbols except basic punctuation (-.,:/()%) and preserve all word & Indic characters
    cleaned = re.sub(r'[^\w\s\-\.\,\:\/\(\)\%\u0900-\u0D7F]', '', cleaned)
    # Standardize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # Safeguard: if metadata artifacts or binary leaks persist, return the clean placeholder
    if (
        "opensource anonymous D" in cleaned
        or "unspecified D" in cleaned
        or "opensource (anonymous D" in raw_text
    ):
        return PLACEHOLDER_TEXT

    # Check if cleaned text has fewer than 10 meaningful characters (English letters or Indic scripts)
    if len(re.findall(r'[\w\u0900-\u0D7F]', cleaned)) < 10:
        return PLACEHOLDER_TEXT

    return cleaned


def ingest_pdf_to_standard_entry(pdf_source, standard_number=None, title=None, category="Electrical & Procurement", status="Active", version_year="2026"):
    """
    Utility function to parse an uploaded PDF file, extract clean text, and format a standard entry dictionary.
    """
    raw_text = extract_text_from_pdf(pdf_source)
    cleaned_desc = clean_extracted_text(raw_text)

    snippet = cleaned_desc[:600] if len(cleaned_desc) > 600 else cleaned_desc

    timestamp = int(time.time())
    std_id = f"BIS-PDF-{timestamp}"
    std_no = standard_number if standard_number else f"IS-REG-{timestamp % 10000}"
    std_title = title if title else "Ingested Regulatory PDF Specification"

    return {
        "standard_id": std_id,
        "standard_number": std_no,
        "title": std_title,
        "description": snippet,
        "status": status,
        "category": category,
        "version_year": str(version_year)
    }


def append_entry_to_csv(entry, csv_path="data/standard.csv"):
    """
    Appends a new standard entry dictionary to the CSV dataset.
    """
    file_exists = os.path.exists(csv_path)
    fieldnames = ["standard_id", "standard_number", "title", "description", "status", "category", "version_year"]

    with open(csv_path, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists or os.path.getsize(csv_path) == 0:
            writer.writeheader()
        writer.writerow(entry)
    return True


if __name__ == "__main__":
    print("PDF Ingestion module loaded successfully.")