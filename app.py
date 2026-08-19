import ctypes
import logging
import os
import socket
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import uvicorn
import webbrowser
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

def is_admin():
    """Retourne True si l'application est exécutée avec les droits administrateur."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def show_first_run_message():
    """Affiche le message expliquant pourquoi les droits administrateur sont nécessaires."""
    ctypes.windll.user32.MessageBoxW(
        0,
        (
            "MaieuticAnalyzer doit effectuer une configuration initiale.\n\n"
            "Pour sécuriser la connexion HTTPS, l'application doit installer "
            "un certificat de confiance sur cet ordinateur.\n\n"
            "Cette opération nécessite les droits administrateur et "
            "ne sera nécessaire qu'une seule fois.\n\n"
            "Cliquez sur OK pour relancer automatiquement MaieuticAnalyzer "
            "avec les droits administrateur."
        ),
        "Première configuration de MaieuticAnalyzer",
        0x40,  # MB_ICONINFORMATION
    )


def relaunch_as_admin():
    """Relance l'application avec élévation UAC."""
    if not getattr(sys, "frozen", False):
        return False

    executable = sys.executable

    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        executable,
        None,
        None,
        1,
    )

    return result > 32


def get_mkcert_path():
    """Retourne le chemin vers mkcert embarqué par PyInstaller."""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "mkcert.exe")

    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "bin",
        "mkcert.exe",
    )


def initialize_certificates():
    """
    Vérifie la présence des certificats et les génère si nécessaire.

    En mode packagé, une première exécution nécessite une élévation UAC
    afin que mkcert puisse installer sa CA dans le magasin Windows.
    """

    if os.name != "nt":
        return (
            os.path.join(BASE_PATH, "certs", "cert.pem"),
            os.path.join(BASE_PATH, "certs", "key.pem"),
        )

    exe_dir = (
        os.path.dirname(sys.executable)
        if getattr(sys, "frozen", False)
        else os.path.dirname(os.path.abspath(__file__))
    )

    cert_path = os.path.join(exe_dir, "cert.pem")
    key_path = os.path.join(exe_dir, "key.pem")

    # Tout est déjà configuré.
    if os.path.exists(cert_path) and os.path.exists(key_path):
        return cert_path, key_path

    # En mode développement, on ne tente pas d'élever le processus.
    if not getattr(sys, "frozen", False):
        raise FileNotFoundError(
            "Certificats absents du répertoire certs/. "
            "Lancez mkcert -install puis générez les certificats."
        )

    # Première installation : il faut les droits administrateur.
    if not is_admin():
        show_first_run_message()

        if not relaunch_as_admin():
            raise RuntimeError(
                "La configuration initiale nécessite les droits administrateur."
            )

        # Le processus actuel doit s'arrêter. Le processus élevé va continuer.
        sys.exit(0)

    mkcert = get_mkcert_path()

    if not os.path.exists(mkcert):
        raise FileNotFoundError(
            f"mkcert.exe introuvable : {mkcert}"
        )

    logging.info("Première configuration HTTPS : installation de mkcert.")

    result = subprocess.run(
        [mkcert, "-install"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Impossible d'installer le certificat racine mkcert.\n\n"
            f"{result.stdout}\n{result.stderr}"
        )

    logging.info("CA mkcert installée.")

    result = subprocess.run(
        [
            mkcert,
            "-cert-file",
            cert_path,
            "-key-file",
            key_path,
            "localhost",
            "127.0.0.1",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Impossible de générer les certificats HTTPS.\n\n"
            f"{result.stdout}\n{result.stderr}"
        )

    logging.info("Certificats HTTPS générés.")

    return cert_path, key_path


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

cert_path, key_path = initialize_certificates()


def wait_and_open_browser():
    """Attend que le serveur HTTPS soit disponible puis ouvre le navigateur."""
    for _ in range(100):
        try:
            with socket.create_connection(
                ("127.0.0.1", 8443),
                timeout=0.2,
            ):
                webbrowser.open("https://localhost:8443")
                return
        except OSError:
            time.sleep(0.1)

def open_browser():
    webbrowser.open("https://localhost:8443")

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
        threading.Thread(
            target=wait_and_open_browser,
            daemon=True,
        ).start()

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