import asyncio
import boto3
import json
import os

SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL", "")
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2")


async def publish_order_event(payload: dict) -> None:
    if not SQS_QUEUE_URL:
        return
    def _send():
        sqs = boto3.client("sqs", region_name=AWS_REGION)
        sqs.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(payload))
    try:
        await asyncio.to_thread(_send)
    except Exception as e:
        print(f"[SQS] publish_order_event 실패: {e}")
