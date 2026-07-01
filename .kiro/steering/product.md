# Cloudage Image Rekognition

## Overview

Cloudage is an AWS-based image processing pipeline that classifies images using Amazon Rekognition and visualizes results in QuickSight. The system accepts image URLs via REST API, runs label detection on each image, persists results in DynamoDB, forwards XML payloads to downstream systems, and enables analytics via Athena federated queries.

## Core Purpose

This is a learning project (workshop) designed to teach AWS serverless patterns. Each Lambda handler contains `TODO` comments with paired `*_solution.py` reference implementations for candidates to learn from.

## Key Capabilities

- **Image Ingestion**: REST API endpoint (`GET /?url=<image_url>&name=<filename>`) for submitting images
- **Automated Classification**: Amazon Rekognition label detection (max 10 labels, 70% confidence minimum)
- **Data Persistence**: Results stored in DynamoDB with searchable schema
- **Event-Driven Pipeline**: SNS/SQS messaging with dead-letter queues (DLQs) on all queues
- **Downstream Integration**: XML conversion and HTTP forwarding to external endpoints (URL from SSM Parameter Store)
- **Analytics & Visualization**: Athena federated queries on DynamoDB data visualized in QuickSight via Glue Data Catalog

## Architecture Pattern

Four interdependent CDK stacks deployed in order:

1. **APIStack** — Image ingestion (API Gateway, Lambda, S3, SNS, SQS)
2. **IntegrationStack** — Downstream forwarding (XML conversion, HTTP POST, S3 XML storage)
3. **RekognitionStack** — Image classification (Rekognition, DynamoDB, Lambda event handlers)
4. **VisualizationStack** — Analytics (Athena SAR connector, Glue crawler, QuickSight data source)

## Key Design Principles

- **Serverless-first**: No servers to manage, event-driven architecture
- **Least privilege IAM**: Each Lambda has minimal required permissions
- **Resilience**: All SQS queues have DLQs and CloudWatch alarms
- **Configuration management**: Runtime config via `cdk.json` context (never hardcoded)
- **Connection reuse**: boto3 clients instantiated at module level for Lambda optimization
- **Logging**: Uses Python `logging` module; no bare `print()` statements
- **Reference implementations**: `*_solution.py` files are read-only for learning
