import json
from groq import Groq
from core.config import settings
from utils.pdf_parser import extract_text_from_pdf
from utils.pptx_parser import extract_text_from_pptx
from models.pitch import PitchExtractedData

# Configuration Groq (gratuit, rapide, fiable)
client = Groq(api_key=settings.groq_api_key)

EXTRACTION_PROMPT = """You are an expert startup analyst. Extract the key business information from the following pitch deck text.

Return ONLY a valid JSON object with this exact structure (no markdown, no explanation, no backticks):
{
  "startup_name": "Name of the startup",
  "industry": "Primary industry (e.g. FinTech, GreenTech, HealthTech, EdTech, SaaS, etc.)",
  "stage": "Current stage (Idea / MVP / Pre-Seed / Seed / Series A / etc.)",
  "country": "Country of the startup",
  "problem": "The problem being solved (2-3 sentences)",
  "solution": "The proposed solution (2-3 sentences)",
  "market_size": "Market size information (TAM/SAM/SOM if mentioned, otherwise estimate)",
  "business_model": "How the startup makes money",
  "team": "Team description (founders, key members)",
  "traction": "Traction metrics if mentioned (users, revenue, clients...), or null",
  "funding_needed": "Amount of funding being sought if mentioned, or null",
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
}

Important: If this is not a pitch deck, still extract whatever business-relevant information you can find.

Document content:
"""


def extract_file_text(file_path: str, filename: str) -> str:
    ext = filename.lower().split(".")[-1]
    if ext == "pdf":
        return extract_text_from_pdf(file_path)
    elif ext in ("pptx", "ppt"):
        return extract_text_from_pptx(file_path)
    else:
        raise ValueError(f"Format non supporté: {ext}. Utilisez PDF ou PPTX.")


def extract_pitch_data(file_path: str, filename: str) -> PitchExtractedData:
    # Étape 1 : extraction texte brut
    raw_text = extract_file_text(file_path, filename)

    if not raw_text.strip():
        raise ValueError("Aucun texte extrait du fichier. Vérifiez que le PDF n'est pas scanné.")

    # Étape 2 : appel Groq (LLaMA 3.3 70B — gratuit)
    response = client.chat.completions.create(
        model=settings.extraction_model,
        messages=[
            {
                "role": "user",
                "content": EXTRACTION_PROMPT + raw_text[:8000]
            }
        ],
        temperature=0.1,
        max_tokens=1500,
    )

    response_text = response.choices[0].message.content.strip()

    # Étape 3 : nettoyage + parse JSON
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()

    data = json.loads(response_text)

    # Fix : le LLM retourne parfois la string "null" au lieu de None
    if data.get("funding_needed") in ("null", "None", "", "N/A", "Not specified"):
        data["funding_needed"] = None
    if data.get("traction") in ("null", "None", "", "N/A", "Not specified"):
        data["traction"] = None

    data["raw_text"] = raw_text

    return PitchExtractedData(**data)