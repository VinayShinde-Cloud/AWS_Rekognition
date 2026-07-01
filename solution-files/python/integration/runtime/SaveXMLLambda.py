"""Lambda function to support the DIY Integration service"""

import json
import logging
import os
import time

import boto3
import botocore.exceptions

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")
S3_BUCKET = os.getenv("BUCKET_NAME")
FILE_PATH = os.getenv("FILE_PATH", "received/payload.xml")


def save_to_s3(bucket, key, data):
    """Save file to S3.

    Uses a timestamped key so each payload is stored individually rather than
    overwriting the previous one. The base FILE_PATH env var is used as a
    prefix, with a millisecond epoch suffix appended.

    Args:
        bucket (str): S3 bucket name
        key (str): S3 object key (used as prefix; timestamp appended)
        data (str | bytes): Payload to store

    Returns:
        str: The final S3 key the object was written to
    """
    # Build a unique key: e.g. received/payload_1716480000123.xml
    base, ext = (key.rsplit(".", 1) + [""])[:2]
    ext = f".{ext}" if ext else ""
    timestamped_key = f"{base}_{int(time.time() * 1000)}{ext}"

    try:
        s3_client.put_object(Body=data, Bucket=bucket, Key=timestamped_key)
        logger.info("Saved payload to s3://%s/%s", bucket, timestamped_key)
        return timestamped_key
    except botocore.exceptions.ClientError as e:
        logger.error("Error saving file to S3: %s", e)
        raise


def handler(event, context):
    """Lambda handler"""
    body = event.get("body")
    if not body:
        logger.warning("Received request with empty or missing body")
        return {
            "statusCode": 400,
            "body": json.dumps("Bad Request: body is required"),
        }

    try:
        saved_key = save_to_s3(S3_BUCKET, FILE_PATH, body)
    except botocore.exceptions.ClientError as e:
        logger.error("S3 write failed: %s", e)
        return {
            "statusCode": 500,
            "body": json.dumps(f"Error saving payload: {str(e)}"),
        }
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        return {
            "statusCode": 500,
            "body": json.dumps(f"Unexpected error: {str(e)}"),
        }

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Saved", "key": saved_key}),
    }
