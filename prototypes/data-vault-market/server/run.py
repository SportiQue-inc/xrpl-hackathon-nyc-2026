"""Start the Data Vault Market: python run.py  (then open http://localhost:8800)."""
import os
import uvicorn

if __name__ == "__main__":
    uvicorn.run("vaultmarket.app:app", host=os.environ.get("VM_HOST", "0.0.0.0"), port=int(os.environ.get("VM_PORT", "8800")))
