import os
import boto3
import json

table_name = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb")


def scan_table():
    """
    Scan all items from the DynamoDB table.

    Returns:
        list: All items from the DynamoDB table
    """
    table = dynamodb.Table(table_name)
    response = table.scan()
    items = response.get("Items", [])

    # Handle pagination — DynamoDB returns up to 1 MB per call
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    return items


def handler(event, context):
    """
    Lambda handler function to list all images from DynamoDB.

    Args:
        event: Lambda event object
        context: Lambda context object

    Returns:
        dict: API Gateway proxy response with statusCode and JSON body
    """
    try:
        items = scan_table()
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"images": items}),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": str(e)}),
        }
