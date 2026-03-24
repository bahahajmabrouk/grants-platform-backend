FROM python:3.11-slim

WORKDIR /app

# Dépendances système pour PyMuPDF et Playwright
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installation Playwright browsers
RUN playwright install chromium --with-deps

COPY . .

# Dossier uploads
RUN mkdir -p uploads

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
