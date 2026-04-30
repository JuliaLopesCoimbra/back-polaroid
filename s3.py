import os
import boto3
from loguru import logger

BUCKET = os.getenv("AWS_S3_BUCKET", "polaroid-event-fotos")
REGION = os.getenv("AWS_REGION", "us-east-1")


def _get_client():
    return boto3.client(
        "s3",
        region_name=REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def upload_photo(file_path: str, key: str) -> str:
    client = _get_client()
    logger.info(f"S3 upload started: bucket={BUCKET} key={key}")
    print(f"[S3] Upload started: bucket={BUCKET} key={key}", flush=True)
    try:
        with open(file_path, "rb") as f:
            client.put_object(
                Bucket=BUCKET,
                Key=key,
                Body=f,
                ContentType="image/png",
                ACL="public-read",
            )
        url = f"https://{BUCKET}.s3.{REGION}.amazonaws.com/{key}"
        logger.info(f"S3 upload completed: {url}")
        print(f"[S3] Upload completed: {url}", flush=True)
        return url
    except Exception as exc:
        logger.exception(f"S3 upload failed: bucket={BUCKET} key={key} error={exc}")
        print(f"[S3] Upload failed: bucket={BUCKET} key={key} error={exc}", flush=True)
        raise
