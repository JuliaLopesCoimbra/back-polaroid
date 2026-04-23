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
    with open(file_path, "rb") as f:
        client.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=f,
            ContentType="image/png",
            ACL="public-read",
        )
    url = f"https://{BUCKET}.s3.{REGION}.amazonaws.com/{key}"
    logger.info(f"Uploaded → {url}")
    return url
