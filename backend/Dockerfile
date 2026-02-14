FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Create non-root user
RUN addgroup --system app && adduser --system --ingroup app app

# Install dependencies first for layer caching
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy app source
COPY app/ ./app/

# Create writable paths and set ownership
RUN mkdir -p /app/data /tmp && chown -R app:app /app /tmp

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
