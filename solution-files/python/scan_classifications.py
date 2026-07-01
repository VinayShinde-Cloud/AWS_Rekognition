#!/usr/bin/env python3
"""
scan_classifications.py — Scan and display items from the Rekognition
Classifications DynamoDB table.

The table name is resolved automatically from cdk-outputs-RekognitionStack.json
(written by deploy.sh). No hardcoded table names needed.

Usage:
    python scan_classifications.py                        # scan table
    python scan_classifications.py --json                 # raw JSON output
    python scan_classifications.py --table <table-name>   # explicit table name
    python scan_classifications.py --region us-east-1  # explicit region
    python scan_classifications.py --profile my-profile   # explicit AWS profile

To send real images through the pipeline:
    python send_images.py
"""

import json
import os
import argparse

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


def _resolve_table_name() -> str:
    """
    Resolve the DynamoDB table name from the CDK outputs file.
    Falls back to the --table CLI argument if the file is not found.
    """
    outputs_file = os.path.join(
        os.path.dirname(__file__), "cdk-outputs-RekognitionStack.json"
    )
    if os.path.exists(outputs_file):
        with open(outputs_file) as f:
            outputs = json.load(f)
        table_name = outputs.get("RekognitionStack", {}).get("ClassificationsTableName")
        if table_name:
            return table_name
    return ""


def scan_table(table_name: str, dynamodb) -> list:
    """
    Scan all items from a DynamoDB table, handling pagination automatically.
    """
    table = dynamodb.Table(table_name)
    response = table.scan()
    items = response.get("Items", [])

    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    return items


def print_table(items: list, table_name: str) -> None:
    """Pretty-print Rekognition classification items."""
    if not items:
        print("No items found in the table.")
        print("Send images through the pipeline first:")
        print("  python send_images.py")
        return

    print(f"\n{'═' * 80}")
    print(f"  Rekognition Classifications — {table_name}")
    print(f"  Items returned: {len(items)}")
    print(f"{'═' * 80}")

    for i, item in enumerate(items, 1):
        print(f"\n  [{i:>3}] {item.get('image', 'N/A')}")
        print(f"        Labels : {item.get('labels', [])}")
        print(f"        {'─' * 74}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Scan the Rekognition Classifications DynamoDB table"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="AWS CLI profile name (optional)",
    )
    parser.add_argument(
        "--table",
        default=None,
        help="DynamoDB table name (auto-resolved from cdk-outputs-RekognitionStack.json if omitted)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted table",
    )
    args = parser.parse_args()

    # Resolve table name
    table_name = args.table or _resolve_table_name()
    if not table_name:
        print("Error: Could not resolve DynamoDB table name.")
        print("Either:")
        print("  1. Deploy RekognitionStack first (deploy.sh creates cdk-outputs-RekognitionStack.json)")
        print("  2. Pass --table <table-name> explicitly")
        raise SystemExit(1)

    session_kwargs = {"region_name": args.region}
    if args.profile:
        session_kwargs["profile_name"] = args.profile

    session = boto3.Session(**session_kwargs)
    dynamodb = session.resource("dynamodb")

    try:
        print(f"Scanning table: {table_name} (region: {args.region})")
        items = scan_table(table_name, dynamodb)

        if args.json:
            print(json.dumps(items, indent=2, default=str))
        else:
            print_table(items, table_name)

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ResourceNotFoundException":
            print(f"Error: Table '{table_name}' not found in region '{args.region}'.")
            print("Deploy RekognitionStack first: ./deploy.sh")
        elif error_code == "AccessDeniedException":
            print("Error: Access denied. Ensure your IAM credentials have dynamodb:Scan permission.")
        else:
            print(f"AWS error ({error_code}): {e.response['Error']['Message']}")
    except NoCredentialsError:
        print("Error: No AWS credentials found.")
        print("Configure via 'aws configure', environment variables, or --profile.")


if __name__ == "__main__":
    main()
