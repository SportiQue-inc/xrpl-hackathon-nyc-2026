# Data Vault Market server. Build from the repository root (it imports agentrail/ledger):
#   docker build -f prototypes/data-vault-market/server/Dockerfile .
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt python-multipart anthropic
COPY agentrail ./agentrail
COPY prototypes/data-vault-market/server ./prototypes/data-vault-market/server
WORKDIR /app/prototypes/data-vault-market/server
# DB, wallet seeds and keys live on the mounted disk, so restarts keep the market and its wallets
ENV VM_DATA_DIR=/data VM_PUBLIC=1 VM_HOST=0.0.0.0 PYTHONUNBUFFERED=1
CMD ["sh", "-c", "VM_PORT=${PORT:-8800} exec python run.py"]
