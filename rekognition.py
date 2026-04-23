import os
import boto3
from loguru import logger

COLLECTION_ID = os.getenv("REKOGNITION_COLLECTION_ID", "polaroid-event")


def _get_client():
    return boto3.client(
        "rekognition",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def ensure_collection() -> None:
    client = _get_client()
    existing = client.list_collections().get("CollectionIds", [])
    if COLLECTION_ID not in existing:
        client.create_collection(CollectionId=COLLECTION_ID)
        logger.info(f"Created Rekognition collection: {COLLECTION_ID}")
    else:
        logger.info(f"Rekognition collection ready: {COLLECTION_ID}")


def index_face(image_bytes: bytes, photo_id: str) -> str:
    client = _get_client()
    response = client.index_faces(
        CollectionId=COLLECTION_ID,
        Image={"Bytes": image_bytes},
        ExternalImageId=photo_id,
        DetectionAttributes=[],
        MaxFaces=1,
        QualityFilter="AUTO",
    )
    records = response.get("FaceRecords", [])
    if not records:
        raise ValueError(f"No face detected in photo {photo_id}")
    face_id = records[0]["Face"]["FaceId"]
    logger.info(f"Indexed face {face_id} → photo_id={photo_id}")
    return face_id


def search_face(image_bytes: bytes) -> tuple:
    """Returns (photo_id, confidence) or (None, 0.0) when no match found."""
    client = _get_client()
    try:
        response = client.search_faces_by_image(
            CollectionId=COLLECTION_ID,
            Image={"Bytes": image_bytes},
            MaxFaces=1,
            FaceMatchThreshold=80.0,
        )
        matches = response.get("FaceMatches", [])
        if not matches:
            logger.info("No face match found in collection")
            return None, 0.0
        best = matches[0]
        photo_id = best["Face"]["ExternalImageId"]
        confidence = best["Similarity"]
        logger.info(f"Face match: photo_id={photo_id}  confidence={confidence:.1f}%")
        return photo_id, confidence
    except client.exceptions.InvalidParameterException:
        logger.warning("No face detected in search image")
        return None, 0.0
