FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Environment variables
ENV HOST=0.0.0.0
ENV PORT=8000
ENV HYPERLIQUID_API_URL=https://api.hyperliquid.xyz
# ENV TARGET_BUILDER=0x...

EXPOSE 8000

# Run the application
CMD ["python", "-m", "src.main"]
