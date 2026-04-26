"""
Limpa fotos no bucket S3 do projeto.

Por padrão, remove objetos com o prefixo "polaroids/".

Uso:
    python clear_bucket_photos.py --confirm
    python clear_bucket_photos.py --prefix polaroids/ --confirm
"""

import argparse
import os

import boto3
from dotenv import load_dotenv


def get_client(region: str):
    return boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def iter_keys(client, bucket: str, prefix: str):
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            yield obj["Key"]


def delete_by_prefix(client, bucket: str, prefix: str) -> int:
    deleted = 0
    batch = []

    for key in iter_keys(client, bucket, prefix):
        batch.append({"Key": key})
        if len(batch) == 1000:
            client.delete_objects(Bucket=bucket, Delete={"Objects": batch})
            deleted += len(batch)
            batch = []

    if batch:
        client.delete_objects(Bucket=bucket, Delete={"Objects": batch})
        deleted += len(batch)

    return deleted


def main():
    parser = argparse.ArgumentParser(description="Apaga fotos do bucket S3 por prefixo.")
    parser.add_argument("--prefix", default="polaroids/", help='Prefixo para apagar (padrão: "polaroids/").')
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirma a exclusão. Sem este parâmetro, nada é apagado.",
    )
    args = parser.parse_args()

    load_dotenv()

    bucket = os.getenv("AWS_S3_BUCKET", "polaroid-event-fotos")
    region = os.getenv("AWS_REGION", "us-east-1")

    if not args.confirm:
        print("Nenhuma ação executada.")
        print(f"Use --confirm para apagar objetos em s3://{bucket}/{args.prefix}")
        return

    client = get_client(region)
    total = delete_by_prefix(client, bucket, args.prefix)
    print(f"Exclusão concluída: {total} objeto(s) removido(s) de s3://{bucket}/{args.prefix}")


if __name__ == "__main__":
    main()
