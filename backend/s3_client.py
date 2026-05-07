import boto3, os
from botocore.config import Config

ENDPOINT   = os.environ["WS_S3_ENDPOINT"]   # np. https://s3.poland.whitesky.cloud
BUCKET     = os.environ.get("WS_S3_BUCKET", "spozywka")
ACCESS_KEY = os.environ["WS_S3_ACCESS_KEY"]
SECRET_KEY = os.environ["WS_S3_SECRET_KEY"]
PUBLIC_BASE = os.environ.get("WS_S3_PUBLIC_BASE", f"{ENDPOINT}/{BUCKET}")


def _client():
    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=Config(signature_version="s3v4"),
    )


def upload_photo(session_id: str, filename: str, data: bytes, content_type: str = "image/jpeg") -> str:
    key = f"{session_id}/raw/{filename}"
    _client().put_object(
        Bucket=BUCKET,
        Key=key,
        Body=data,
        ContentType=content_type,
        ACL="public-read",
    )
    return f"{PUBLIC_BASE}/{key}"


def upload_processed(session_id: str, filename: str, data: bytes, content_type: str = "image/jpeg") -> str:
    key = f"{session_id}/processed/{filename}"
    _client().put_object(
        Bucket=BUCKET,
        Key=key,
        Body=data,
        ContentType=content_type,
        ACL="public-read",
    )
    return f"{PUBLIC_BASE}/{key}"


def list_keys(prefix: str) -> list[str]:
    resp = _client().list_objects_v2(Bucket=BUCKET, Prefix=prefix)
    return [o["Key"] for o in resp.get("Contents", [])]


def delete_prefix(prefix: str):
    keys = list_keys(prefix)
    if not keys:
        return
    _client().delete_objects(
        Bucket=BUCKET,
        Delete={"Objects": [{"Key": k} for k in keys]}
    )
