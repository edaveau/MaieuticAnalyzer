import logging
import os
import shutil
import sys
import tempfile
import traceback
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from processing import load_and_clean_excel, compute_retrocessions

# Piège à erreurs de démarrage — écrit AVANT toute initialisation
_crash_log = os.path.join(os.path.expanduser("~"), "MaieuticAnalyzer_crash.log")


def _excepthook(exc_type, exc_value, exc_tb):
    with open(_crash_log, "w", encoding="utf-8") as f:
        traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = _excepthook


def get_base_path():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


BASE_PATH = get_base_path()

templates_path = os.path.join(BASE_PATH, "templates")
static_path = os.path.join(BASE_PATH, "static")


def find_cert(filename: str) -> str:
    """
    Cherche un certificat dans cet ordre de priorité :
    1. À côté de l'exe (déposé par l'installeur)
    2. Dans _MEIPASS (embarqué dans le binaire PyInstaller)
    3. Dans certs/ (mode développement)
    """
    candidates = []

    if getattr(sys, "frozen", False):
        # Priorité 1 : dossier de l'exe (installeur)
        candidates.append(os.path.join(os.path.dirname(sys.executable), filename))
        # Priorité 2 : _MEIPASS (embarqué)
        candidates.append(os.path.join(sys._MEIPASS, filename))
    else:
        # Mode dev : sous-dossier certs/
        candidates.append(os.path.join(BASE_PATH, "certs", filename))

    for path in candidates:
        if os.path.exists(path):
            logging.info(f"Certificat trouvé : {path}")
            return path

    raise FileNotFoundError(
        f"Certificat '{filename}' introuvable. Chemins essayés : {candidates}"
    )


cert_path = find_cert("cert.pem")
key_path = find_cert("key.pem")

# Logs portables Windows/Linux
if os.name == "nt":
    log_base = os.getenv("APPDATA", os.path.expanduser("~"))
else:
    log_base = os.path.expanduser("~/.local/share")

LOG_DIR = os.path.join(log_base, "MaieuticAnalyzer", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, "app.log")

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
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
        return result
    except Exception as e:
        logging.exception("Erreur lors du traitement du fichier.")
        # On retourne TOUJOURS du JSON, même en cas d'erreur
        return JSONResponse(status_code=500, content={"error": True, "detail": str(e)})
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.exception("Erreur non catchee")
    return JSONResponse(status_code=500, content={"error": True, "detail": str(exc)})


if __name__ == "__main__":
    try:
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8443,
            ssl_certfile=cert_path,
            ssl_keyfile=key_path,
            log_config=None,
            log_level="warning",
        )
    except Exception:
        with open(_crash_log, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise
