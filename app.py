from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
import shutil
import os
import logging

from processing import load_and_clean_excel, compute_retrocessions

app = FastAPI()

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
    <body>
        <h2>Calcul rétrocessions</h2>
        <form action="/upload" method="post" enctype="multipart/form-data">
            IK: <input type="text" name="ik" value="0.61"><br>
            IF: <input type="text" name="if_val" value="4"><br>
            MD: <input type="text" name="md" value="10"><br><br>

            <input type="file" name="file">
            <input type="submit">
        </form>
    </body>
    </html>
    """


@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    ik: float = Form(...),
    if_val: float = Form(...),
    md: float = Form(...),
):
    temp_path = f"temp_{file.filename}"

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    df = load_and_clean_excel(temp_path)
    result = compute_retrocessions(df, ik, if_val, md)

    os.remove(temp_path)

    return result
