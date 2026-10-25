# AgentRail engine (UniQLab console, UniQdata participant app, /live, /demo) as one web service.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agentrail agentrail
COPY apps apps
COPY fixtures fixtures
COPY xrpl_checks xrpl_checks
ENV PYTHONUNBUFFERED=1
CMD ["sh", "-c", "uvicorn agentrail.web:app --host 0.0.0.0 --port ${PORT:-8000}"]
