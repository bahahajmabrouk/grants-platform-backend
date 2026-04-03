import fitz  # PyMuPDF
from pathlib import Path


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extrait tout le texte d'un PDF page par page.
    Retourne le texte brut concaténé.
    """
    text_content = []
    
    with fitz.open(file_path) as doc:
        for page_num, page in enumerate(doc):
            text = page.get_text("text")
            if text.strip():
                text_content.append(f"--- Page {page_num + 1} ---\n{text}")
    
    return "\n\n".join(text_content)


def get_pdf_metadata(file_path: str) -> dict:
    """Extrait les métadonnées du PDF (titre, auteur, nb pages)"""
    with fitz.open(file_path) as doc:
        meta = doc.metadata
        return {
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "page_count": doc.page_count,
            "file_size_kb": round(Path(file_path).stat().st_size / 1024, 1),
        }
