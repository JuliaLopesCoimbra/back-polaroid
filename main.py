import time
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

from drive import watch_folder, mark_processed, POLL_INTERVAL
from polaroid import apply_polaroid_frame
from rekognition import ensure_collection, index_face
from s3 import upload_photo

OUTPUT_DIR = Path(__file__).parent / "data" / "output"


def with_retry(func, *args, max_retries: int = 3, **kwargs):
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.warning(f"[{func.__name__}] attempt {attempt} failed: {exc}. Retry in {wait}s")
                time.sleep(wait)
            else:
                logger.error(f"[{func.__name__}] all {max_retries} attempts failed: {exc}")
                raise


def process_photo(file_info: dict, processed: dict, processed_ids: set) -> None:
    file_id = file_info["id"]
    file_name = file_info["name"]
    local_path = str(file_info["path"])
    photo_id = str(uuid.uuid4())

    logger.info(f"--- Processing: {file_name} → {photo_id} ---")
    print(f"[PROCESS] Iniciando processamento: nome={file_name} id={file_id} photo_id={photo_id}", flush=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    polaroid_path = str(OUTPUT_DIR / f"{photo_id}.png")

    logger.info(f"Generating polaroid frame for {file_name}")
    print(f"[PROCESS] Gerando moldura para: {file_name}", flush=True)
    with_retry(apply_polaroid_frame, local_path, polaroid_path)

    with open(polaroid_path, "rb") as f:
        image_bytes = f.read()

    logger.info(f"Indexing face on Rekognition for photo_id={photo_id}")
    print(f"[REKOGNITION] Indexando face: photo_id={photo_id}", flush=True)
    with_retry(index_face, image_bytes, photo_id)

    s3_key = f"polaroids/{photo_id}.png"
    logger.info(f"Starting upload to S3: key={s3_key}")
    print(f"[S3] Iniciando upload: {s3_key}", flush=True)
    s3_url = with_retry(upload_photo, polaroid_path, s3_key)
    print(f"[S3] Upload concluido: {s3_url}", flush=True)

    Path(local_path).unlink(missing_ok=True)
    Path(polaroid_path).unlink(missing_ok=True)

    entry = {
        "original_name": file_name,
        "s3_url": s3_url,
        "photo_id": photo_id,
        "timestamp": datetime.utcnow().isoformat(),
    }
    mark_processed(file_id, entry, processed, processed_ids)
    logger.success(f"Done: {file_name} → {s3_url}")
    print(f"[DONE] Processamento concluido: {file_name} -> {s3_url}", flush=True)


def main() -> None:
    logger.info("Polaroid Robot starting up...")
    ensure_collection()

    while True:
        try:
            new_files, processed, processed_ids = watch_folder()
            if not new_files:
                logger.debug("No new files found")
            for file_info in new_files:
                try:
                    process_photo(file_info, processed, processed_ids)
                except Exception as exc:
                    logger.error(f"Failed to process {file_info['name']}: {exc}")
        except Exception as exc:
            logger.error(f"Watch loop error: {exc}")

        logger.debug(f"Sleeping {POLL_INTERVAL}s...")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
