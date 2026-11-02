FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
COPY backend/ backend/
RUN pip install --no-cache-dir .
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5')"
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
