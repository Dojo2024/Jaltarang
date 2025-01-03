import fitz

def extract_text_from_pdf(pdf_file):
    """Extracts text from a PDF file using PyMuPDF (fitz)."""
    text = ""
    try:
        pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            text += page.get_text("text")
        pdf_document.close()
        return text
    except Exception as e:
        return f"Error extracting text from PDF: {e}"


def extract_text_from_md(md_file):
    """Extracts text from a markdown file."""
    try:
        text = md_file.read().decode("utf-8")
        return text
    except Exception as e:
        return f"Error extracting text from markdown: {e}"


def extract_text_from_file(file):
    """Extracts text from the uploaded file based on its type."""
    if file.name.endswith(".pdf"):
        return extract_text_from_pdf(file)
    elif file.name.endswith(".md"):
        return extract_text_from_md(file)
    else:
        return "Unsupported file format. Please upload a PDF or MD file."
