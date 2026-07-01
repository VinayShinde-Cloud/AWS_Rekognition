import os
import boto3
import json
import logging
import urllib.parse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = boto3.client("sqs")
rekognition = boto3.client("rekognition")
dynamodb = boto3.client("dynamodb")
sns = boto3.client("sns")

queue_url = os.environ["SQS_QUEUE_URL"]
table_name = os.environ["TABLE_NAME"]
topic_arn = os.environ["TOPIC_ARN"]

# TODO: Implement detect_labels function
# KIRO PROMPT: "Create a Python function called detect_labels that uses Amazon Rekognition to detect labels in an S3 image with max 10 labels and 70% confidence"
# Expected: Function takes bucket_name and key parameters, returns rekognition.detect_labels() response

def detect_labels(bucket_name, key):
    """
    Detects labels in an image stored in S3 using Amazon Rekognition.
    
    Args:
        bucket_name (str): S3 bucket name
        key (str): S3 object key
        
    Returns:
        dict: Rekognition response with detected labels
    """
    return rekognition.detect_labels(
        Image={
            "S3Object": {
                "Bucket": bucket_name,
                "Name": key,
            }
        },
        MaxLabels=10,
        MinConfidence=70,
    )


# TODO: Implement write_labels_to_db function
# KIRO PROMPT: "Create a Python function called write_labels_to_db that writes an item to DynamoDB using boto3"
# Expected: Function takes table_name and item parameters, calls dynamodb.put_item()

def write_labels_to_db(table_name, item):
    """
    Writes labels to a DynamoDB table.
    
    Args:
        table_name (str): DynamoDB table name
        item (dict): Item to write to DynamoDB
        
    Returns:
        dict: DynamoDB put_item response
    """
    return dynamodb.put_item(
        TableName=table_name,
        Item=item,
    )


# TODO: Implement triggerSNS function
# KIRO PROMPT: "Create a Python function called triggerSNS that publishes a message to an SNS topic"
# Expected: Function takes message parameter, publishes to topic_arn with subject "Success!"

def triggerSNS(message):
    """
    Publishes a message to an SNS topic.
    
    Args:
        message (str): Message to publish
        
    Returns:
        dict: SNS publish response
    """
    return sns.publish(
        TopicArn=topic_arn,
        Message=message,
        Subject="Success!",
    )


# TODO: Implement delete_message function
# KIRO PROMPT: "Create a Python function called delete_message that deletes a message from an SQS queue using receipt handle"
# Expected: Function takes receipt_handle parameter, calls sqs.delete_message()

def delete_message(receipt_handle):
    """
    Deletes a message from the SQS queue.
    
    Args:
        receipt_handle (str): SQS message receipt handle
        
    Returns:
        dict: SQS delete_message response
    """
    return sqs.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=receipt_handle,
    )


def handler(event, context):
    logger.info("Received event:")
    logger.info(event)
    logger.info(type(event))
    try:
        # process message from SQS
        for Record in event.get("Records", []):
            receipt_handle = Record.get("receiptHandle")
            logger.info(f"Processing message with receipt handle: {receipt_handle}")
            
            body = Record.get("body")
            if isinstance(body, str):
                body = json.loads(body)
            
            for record in body.get("Records", []):
                bucket_name = record.get("s3", {}).get("bucket", {}).get("name")
                key = urllib.parse.unquote_plus(record.get("s3", {}).get("object", {}).get("key"))
                
                logger.info(f"Processing image: s3://{bucket_name}/{key}")

                try:
                    # Call detect_labels function
                    logger.info("Calling Rekognition detect_labels...")
                    labels = detect_labels(bucket_name, key)
                    logger.info(f"Detected labels: {labels}")

                    # code snippet to create dynamodb item from labels
                    db_result = []
                    if labels and labels.get("Labels"):
                        json_labels = json.dumps(labels["Labels"])
                        db_labels = json.loads(json_labels)
                        for label in db_labels:
                            db_result.append(label["Name"])
                    
                    logger.info(f"Labels for DynamoDB: {db_result}")
                    db_item = {"image": {"S": key}, "labels": {"S": str(db_result)}}

                    # Call write_labels_to_db function
                    logger.info("Writing to DynamoDB...")
                    write_labels_to_db(table_name, db_item)
                    logger.info("Successfully wrote to DynamoDB")

                    # Call triggerSNS function
                    logger.info("Publishing to SNS...")
                    triggerSNS(str(db_result))
                    logger.info("Successfully published to SNS")

                    # Call delete_message function
                    logger.info("Deleting message from SQS...")
                    delete_message(receipt_handle)
                    logger.info("Successfully deleted message from SQS")

                except Exception as image_error:
                    # CRITICAL FIX: Comprehensive error handling for individual images
                    logger.error(f"Error processing image s3://{bucket_name}/{key}: {str(image_error)}", exc_info=True)
                    
                    # Determine error type and log appropriately
                    if isinstance(image_error, sqs.exceptions.InvalidParameterException):
                        logger.error("Rekognition: Invalid image parameters")
                    elif isinstance(image_error, Exception) and "InvalidImageFormat" in str(image_error):
                        logger.error(f"Rekognition: Invalid image format for {key}")
                    elif isinstance(image_error, Exception) and "ImageTooLarge" in str(image_error):
                        logger.error(f"Rekognition: Image too large for {key}")
                    elif isinstance(image_error, Exception) and "ImageQuotaExceeded" in str(image_error):
                        logger.warning(f"Rekognition: Service quota exceeded, retrying image {key}")
                    else:
                        logger.error(f"Unexpected error processing {key}: {image_error}")
                    
                    # Don't delete message on error - let it retry via SQS visibility timeout
                    continue

        return {
            "statusCode": 200,
            "body": json.dumps("Successfully processed images")
        }

    except Exception as e:
        logger.error(f"Fatal error in Lambda handler: {str(e)}", exc_info=True)
        logger.error("Error processing object from bucket.")
        raise e
