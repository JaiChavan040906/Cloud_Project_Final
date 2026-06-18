import boto3
from botocore.config import Config

from app.config import AWS_ENDPOINT_URL, AWS_REGION, S3_BUCKET_NAME


def _get_client():
    kwargs = {"region_name": AWS_REGION, "config": Config(retries={"max_attempts": 3})}
    if AWS_ENDPOINT_URL:
        kwargs["endpoint_url"] = AWS_ENDPOINT_URL
    return boto3.client("s3", **kwargs)


def upload_csv(file_content: bytes, key: str) -> bool:
    if not S3_BUCKET_NAME:
        return False
    try:
        client = _get_client()
        client.put_object(Bucket=S3_BUCKET_NAME, Key=key, Body=file_content)
        return True
    except Exception:
        return False


def download_csv(key: str) -> str | None:
    if not S3_BUCKET_NAME:
        return None
    try:
        client = _get_client()
        resp = client.get_object(Bucket=S3_BUCKET_NAME, Key=key)
        return resp["Body"].read().decode("utf-8")
    except Exception:
        return None


def list_csv_files() -> list[str]:
    if not S3_BUCKET_NAME:
        return []
    try:
        client = _get_client()
        resp = client.list_objects_v2(Bucket=S3_BUCKET_NAME)
        return [obj["Key"] for obj in resp.get("Contents", []) if obj["Key"].endswith(".csv")]
    except Exception:
        return []
