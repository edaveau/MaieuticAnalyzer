from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import shutil
import os
import logging
import uvicorn

from processing import load_and_clean_excel, compute_retrocessions

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


@app.get("/", response_class=HTMLResponse)
def home():
    return Path("templates/index.html").read_text(encoding="utf-8")


@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    ik: float = Form(...),
    if_val: float = Form(...),
    md: float = Form(...),
):
    temp_path = f"temp_{file.filename}"

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        df = load_and_clean_excel(temp_path)
        result = compute_retrocessions(df, ik, if_val, md)
    except Exception as e:
        logging.exception("Erreur lors du traitement du fichier.")
        raise HTTPException(status_code=500, detail=str(e))

    os.remove(temp_path)

    return result


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8443,
        ssl_certfile="certs/localhost.pem",
        ssl_keyfile="certs/localhost-key.pem"
    )
