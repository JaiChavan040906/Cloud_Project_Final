import json
import boto3
from botocore.config import Config
from app.config import AWS_REGION, SQS_QUEUE_URL, AWS_ENDPOINT_URL


def _get_client():
    kwargs = {"region_name": AWS_REGION, "config": Config(retries={"max_attempts": 3})}
    if AWS_ENDPOINT_URL:
        kwargs["endpoint_url"] = AWS_ENDPOINT_URL
    return boto3.client("sqs", **kwargs)


def send_to_sqs(event_data: dict) -> bool:
    if not SQS_QUEUE_URL:
        return False
    try:
        client = _get_client()
        client.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(event_data))
        return True
    except Exception:
        return False


def receive_from_sqs(max_messages: int = 10) -> list[dict]:
    if not SQS_QUEUE_URL:
        return []
    try:
        client = _get_client()
        resp = client.receive_message(QueueUrl=SQS_QUEUE_URL, MaxNumberOfMessages=max_messages)
        return resp.get("Messages", [])
    except Exception:
        return []


def delete_from_sqs(receipt_handle: str) -> bool:
    if not SQS_QUEUE_URL:
        return False
    try:
        client = _get_client()
        client.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt_handle)
        return True
    except Exception:
        return False
