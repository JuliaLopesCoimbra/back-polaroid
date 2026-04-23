import os
import json
import time
import io
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "1q-Qp9V4vwB7jjFeWrrMzVVkIZkMgjC_z")
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
SERVICE_ACCOUNT_FILE = Path(__file__).parent / "service_account.json"
# Dados persistentes ficam em /app/data (volume Docker montado como diretório,
# não como arquivo — montar volume em caminho de arquivo cria um diretório no lugar)
DATA_DIR = Path(__file__).parent / "data"
PROCESSED_FILE = DATA_DIR / "processed.json"
DOWNLOAD_DIR = DATA_DIR / "downloads"
POLL_INTERVAL = 30


def _load_processed() -> dict:
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE, "r") as f:
            return json.load(f)
    return {"processed_files": [], "photos": []}


def _save_processed(data: dict) -> None:
    with open(PROCESSED_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _get_service():
    creds = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE), scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _download_file(service, file_id: str, file_name: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = DOWNLOAD_DIR / file_name
    request = service.files().get_media(fileId=file_id)
    with io.FileIO(str(dest), "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                logger.debug(f"Download {file_name}: {int(status.progress() * 100)}%")
    return dest


def watch_folder(folder_id: str = FOLDER_ID) -> tuple[list, dict, set]:
    service = _get_service()
    processed = _load_processed()
    processed_ids = set(processed["processed_files"])

    logger.info(f"Scanning folder {folder_id} ...")

    query = (
        f"'{folder_id}' in parents and trashed=false and ("
        "mimeType='image/jpeg' or mimeType='image/png'"
        ")"
    )

    results = (
        service.files()
        .list(
            q=query,
            fields="files(id, name, mimeType, createdTime)",
            orderBy="createdTime",
        )
        .execute()
    )
    files = results.get("files", [])
    logger.info(f"Found {len(files)} file(s) in folder, {len(processed_ids)} already processed")

    new_files = []
    for f in files:
        if f["id"] not in processed_ids:
            logger.info(f"New file: {f['name']} ({f['id']})")
            local_path = _download_file(service, f["id"], f["name"])
            new_files.append({"id": f["id"], "name": f["name"], "path": local_path})

    return new_files, processed, processed_ids


def mark_processed(
    file_id: str,
    photo_entry: dict,
    processed: dict,
    processed_ids: set,
) -> None:
    processed_ids.add(file_id)
    processed["processed_files"] = list(processed_ids)
    processed["photos"].append(photo_entry)
    _save_processed(processed)
    logger.debug(f"Marked {file_id} as processed")
