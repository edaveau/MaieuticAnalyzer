from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import shutil
import os
import tempfile
import logging
import uvicorn
import sys
from processing import load_and_clean_excel, compute_retrocessions


def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


BASE_PATH = get_base_path()

templates_path = os.path.join(BASE_PATH, "templates")
static_path = os.path.join(BASE_PATH, "static")
if getattr(sys, 'frozen', False):
    # Dans le bundle PyInstaller, les certs sont à la racine de _MEIPASS
    cert_path = os.path.join(BASE_PATH, "cert.pem")
    key_path = os.path.join(BASE_PATH, "key.pem")
else:
    # En développement, ils sont dans le sous-dossier certs/
    cert_path = os.path.join(BASE_PATH, "certs", "cert.pem")
    key_path = os.path.join(BASE_PATH, "certs", "key.pem")

# Logs portables Windows/Linux
if os.name == 'nt':
    log_base = os.getenv("APPDATA", os.path.expanduser("~"))
else:
    log_base = os.path.expanduser("~/.local/share")

LOG_DIR = os.path.join(log_base, "MaieuticAnalyzer", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, "app.log")

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app = FastAPI()
app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=templates_path)


@app.get("/", response_class=HTMLResponse)
def home():
    index_path = os.path.join(BASE_PATH, "templates", "index.html")
    return Path(index_path).read_text(encoding="utf-8")


@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    ik: float = Form(...),
    if_val: float = Form(...),
    md: float = Form(...),
):
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        temp_path = tmp.name

    try:
        df = load_and_clean_excel(temp_path)
        result = compute_retrocessions(df, ik, if_val, md)
    except Exception as e:
        logging.exception("Erreur lors du traitement du fichier.")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.remove(temp_path)

    return result


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8443,
        ssl_certfile=cert_path,
        ssl_keyfile=key_path,
        log_config=None,
        log_level="warning"
    )