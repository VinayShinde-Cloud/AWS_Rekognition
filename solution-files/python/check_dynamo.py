#!/usr/bin/env python3
"""Simple script to check DynamoDB for image classifications."""

import boto3
import json

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table_name = 'RekognitionStack-Classifications0C921F6C-1VMPN4XOM4W5A'

try:
    table = dynamodb.Table(table_name)
    
    # Scan the table
    response = table.scan()
    items = response.get('Items', [])
    
    print(f"Table: {table_name}")
    print(f"Items found: {len(items)}\n")
    
    if items:
        for i, item in enumerate(items, 1):
            print(f"{i}. Image: {item.get('image')}")
            print(f"   Labels: {item.get('labels')}")
            print()
    else:
        print("No items found in the table.")
        
except Exception as e:
    print(f"Error: {e}")
    raise
