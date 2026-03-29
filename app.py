from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import shutil
import os
import logging
import uvicorn
import sys

from processing import load_and_clean_excel, compute_retrocessions


def get_base_path():
    if getattr(sys, 'frozen', False):
        # mode PyInstaller
        return sys._MEIPASS
    # mode dev
    return os.path.dirname(os.path.abspath(__file__))
BASE_PATH = get_base_path()

templates_path = os.path.join(BASE_PATH, "templates")
static_path = os.path.join(BASE_PATH, "static")

cert_path = os.path.join(BASE_PATH, "cert.pem")
key_path = os.path.join(BASE_PATH, "key.pem")


app = FastAPI()
app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=templates_path)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(os.getenv("APPDATA"), "MaieuticAnalyzer", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, "app.log")

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
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


uvicorn.run(
    "app:app",
    host="127.0.0.1",
    port=8443,
    ssl_certfile=cert_path,
    ssl_keyfile=key_path,
    log_config=None,
    log_level="warning"
)
