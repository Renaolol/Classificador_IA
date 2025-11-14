FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

ENV PORT=8501 \
    STREAMLIT_SERVER_HEADLESS=true

EXPOSE 8501

CMD ["sh", "-c", "streamlit run login.py --server.address=0.0.0.0 --server.port=${PORT:-8501}"]
