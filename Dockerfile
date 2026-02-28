# Build stage
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Production stage
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r mcadv && useradd -r -g mcadv -d /app -s /sbin/nologin mcadv

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Ensure the user owns the working directory
RUN chown -R mcadv:mcadv /app

USER mcadv

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/health')" || exit 1

CMD ["python", "adventure_bot.py", "--distributed-mode"]
