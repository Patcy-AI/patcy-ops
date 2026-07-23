# Patcy Ops — container image for Google Cloud Run.
# A container bundles the app code with the exact Python environment it needs, so it runs the
# same way on Google's servers as it does on your Mac.

FROM python:3.12-slim

# Unbuffered logs (so you see output live in Cloud Run) and no .pyc clutter.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies FIRST (this layer is cached, so rebuilds are fast when only code changes).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app code in.
COPY . .

# Cloud Run routes web traffic to the port in the $PORT env var (default 8080). Streamlit has to
# listen on that exact port and on 0.0.0.0 (all interfaces), or Cloud Run can't reach it.
ENV PORT=8080
EXPOSE 8080

CMD streamlit run app.py \
    --server.port=${PORT} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
