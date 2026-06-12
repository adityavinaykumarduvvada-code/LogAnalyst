# --- stage 1: build the React frontend ---
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- stage 2: Python backend, serving the built frontend ---
FROM python:3.12-slim
WORKDIR /app

# System deps for scikit-learn's compiled wheels are already covered by
# the manylinux wheels on PyPI, so no extra build tools needed here.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Log index + uploads should live on a mounted volume in production so
# they survive container restarts - see docker-compose.yml.
ENV INDEX_PATH=/data/index.pkl
ENV UPLOAD_DIR=/data/uploaded_logs
RUN mkdir -p /data

EXPOSE 8000
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
