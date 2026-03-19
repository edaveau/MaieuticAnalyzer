from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import shutil
import os
import logging

from processing import load_and_clean_excel, compute_retrocessions

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

os.makedirs("logs", exist_ok=True)

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
