# Backend service image (FastAPI).
#
# Planned build steps:
#   1. FROM python:3.11-slim
#   2. Install system deps needed for psycopg2 / OCR libs (libpq-dev,
#      build-essential, tesseract-ocr)
#   3. COPY requirements.txt, pip install -r requirements.txt
#   4. COPY app/ into image
#   5. EXPOSE 8000
#   6. CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
#
# Not yet implemented — placeholder only.
# See also docker/Dockerfile.backend, the compose-driven build used by
# docker/docker-compose.yml.
