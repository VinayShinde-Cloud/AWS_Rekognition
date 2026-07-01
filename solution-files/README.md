# 🖼️ Cloudage Image Rekognition

> **Enterprise-grade serverless image processing pipeline on AWS**  
> A production-ready workshop project for learning AWS serverless architecture patterns.

An AWS-based image processing pipeline built with Python and AWS CDK. The system accepts image URLs via a REST API, runs Amazon Rekognition label detection on each image, persists results in DynamoDB, forwards them as XML to downstream endpoints, and visualizes the data in Amazon QuickSight.

**Perfect for:**
- Learning AWS serverless architecture at scale
- Understanding event-driven pipelines (SNS/SQS)
- Working with AWS CDK Infrastructure as Code
- Building production-grade Lambda functions
- Integrating Rekognition and analytics services

---

## 🚀 Quick Overview

```
┌─────────────────────────────────────────────────────────────┐
│  CLIENT                                                       │
│  GET /?url=<image_url>&name=<filename>                       │
└──────────────┬──────────────────────────────────────────────┘
               │
        ┌──────▼──────────────────────────────────────────────┐
        │  API GATEWAY (APIStack)                            │
        │  ▼ ImageGetAndSaveLambda downloads & saves to S3   │
        └──────┬──────────────────────────────────────────────┘
               │
        ┌──────▼──────────────────────────────────────────────┐
        │  S3 EVENT → SNS → SQS (upload queue)               │
        └──────┬──────────────────────────────────────────────┘
               │
        ┌──────▼──────────────────────────────────────────────┐
        │  IMAGE RECOGNITION (RekognitionStack)              │
        │  ▼ Rekognition DetectLabels                        │
        │  ▼ Store in DynamoDB                               │
        │  ▼ Publish to SNS                                  │
        └──────┬──────────────────────────────────────────────┘
               │
        ┌──────▼──────────────────────────────────────────────┐
        │  INTEGRATION (IntegrationStack)                     │
        │  ▼ Convert to XML                                  │
        │  ▼ HTTP POST to SaveXMLLambda                      │
        │  ▼ Store in S3                                     │
        └────────────────────────────────────────────────────┘

        ┌──────────────────────────────────────────────────┐
        │  ANALYTICS (VisualizationStack)                  │
        │  DynamoDB → Athena → Glue → QuickSight           │
        └──────────────────────────────────────────────────┘
```

---

## 📚 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Deployment Guide](#deployment-guide)
- [API Endpoints](#api-endpoints)
- [Project Structure](#project-structure)
- [Lambda Modules](#lambda-modules)
- [Design Patterns](#design-patterns)
- [IAM & Security](#iam--security)
- [Monitoring & Debugging](#monitoring--debugging)
- [Troubleshooting](#troubleshooting)
- [Learning Objectives](#learning-objectives)

---

## ✨ Features

✅ **REST API** — Upload images via `GET /?url=<image_url>&name=<filename>`  
✅ **Automated Classification** — AWS Rekognition label detection (max 10 labels, 70% confidence)  
✅ **Event-Driven** — SNS/SQS pipeline with dead-letter queues on all queues  
✅ **Data Persistence** — Results stored in DynamoDB with searchable schema  
✅ **XML Integration** — Downstream forwarding via HTTP POST  
✅ **Analytics Ready** — Athena federated queries on DynamoDB data  
✅ **QuickSight Dashboards** — Pre-configured data source for visualization  
✅ **Production Patterns** — Resilience, monitoring, IAM least-privilege  
✅ **Workshop Format** — TODO comments with `*_solution.py` reference implementations  

---

## 🏗️ Architecture

### Four Interdependent Stacks

| Stack | Purpose | Resources |
|-------|---------|-----------|
| **APIStack** | Image ingestion | API Gateway, Lambda, S3, SNS, SQS |
| **IntegrationStack** | Downstream forwarding | Lambda (XML conversion), API endpoint, S3, SSM |
| **RekognitionStack** | Classification | Rekognition, DynamoDB, Lambda event handlers |
| **VisualizationStack** | Analytics | Athena SAR connector, Glue, QuickSight |

### Data Flow (Step by Step)

1. **Client uploads image** via REST API `GET /?url=<image_url>&name=<filename>`
2. **APIStack Lambda** downloads the image from the URL and saves it to S3
3. **S3 event notification** fires `ObjectCreated:Put` → SNS topic → SQS upload queue
4. **RekognitionStack Lambda** (event source: upload queue) polls for new images
5. **Rekognition API** called with `DetectLabels` (max 10 labels, 70% confidence)
6. **Results persisted** to DynamoDB Classifications table
7. **SNS notification** published to image_recognized topic
8. **IntegrationStack Lambda** (event source: rekognized queue) picks up the event
9. **XML conversion** of Rekognition results
10. **HTTP POST** to SaveXMLLambda endpoint (URL from SSM Parameter Store)
11. **SaveXMLLambda** receives XML payload and stores in S3 with timestamped key
12. **Analytics pipeline** queries DynamoDB via Athena federated connector → Glue → QuickSight

---

## 🛠️ Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Language** | Python | 3.11 |
| **Infrastructure as Code** | AWS CDK | 2.118.0 |
| **AWS SDK** | boto3 + botocore | 1.34.144+ |
| **Lambda Layer** | requests library | Latest (requests_layer3_11.zip) |
| **Image Classification** | Amazon Rekognition | DetectLabels API |
| **Object Storage** | Amazon S3 | Latest |
| **NoSQL Database** | Amazon DynamoDB | On-demand billing |
| **Messaging** | SNS + SQS | FIFO-capable |
| **Configuration** | SSM Parameter Store | Latest |
| **Analytics** | Athena + Glue + QuickSight | With DynamoDB connector |
| **Monitoring** | CloudWatch | Alarms, logs, metrics |

---

## 📋 Prerequisites

Before you start, ensure you have:

- **Python 3.11** — `python --version`
- **Node.js** — `npm install -g aws-cdk` (for AWS CDK CLI)
- **AWS CLI v2** — `aws --version` and `aws configure` (with credentials)
- **AWS Account** with:
  - Enough permissions to create Lambda, S3, DynamoDB, Rekognition, etc.
  - **QuickSight subscription** (required for VisualizationStack)
  - Sufficient service quotas (default is usually fine)
- **Git** (for cloning the repository)

### Verify Prerequisites

```bash
# Python 3.11
python --version

# AWS CLI
aws --version
aws sts get-caller-identity

# AWS CDK
cdk --version

# Node.js / npm
npm --version
```

---

## 🚀 Quick Start

### 1. Clone & Setup

```bash
# Clone the repository
git clone https://github.com/VinayShinde-Cloud/AWS_Rekognition.git
cd AWS_Rekognition/solution-files/python

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On Linux/Mac:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure AWS

```bash
# Set AWS credentials and region
aws configure

# Verify credentials
aws sts get-caller-identity
```

### 3. Deploy All Stacks

```bash
# Deploy to us-east-1 (default region)
./deploy.sh --region us-east-1

# Or specify a different region
./deploy.sh --region eu-west-1
```

### 4. Test the Pipeline

```bash
# Get the API endpoint
cat cdk-outputs-APIStack.json

# Upload an image
curl "https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/?url=https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Cat_November_2010-1a.jpg/1200px-Cat_November_2010-1a.jpg&name=cat.jpg"

# List classified images
curl "https://<list-api-id>.execute-api.us-east-1.amazonaws.com/prod/"

# Or use Python to seed test data
python scan_classifications.py --seed --region us-east-1
python scan_classifications.py --region us-east-1
```

---

## 📦 Deployment Guide

### Full Deployment

```bash
# Deploy all 4 stacks (10-15 minutes)
./deploy.sh --region us-east-1
```

**What `deploy.sh` does automatically:**
1. ✓ Validates AWS CLI, CDK, Python venv
2. ✓ Runs `cdk bootstrap` (if needed)
3. ✓ Creates/uploads Lambda layer zip to asset bucket
4. ✓ Detects if image bucket already exists
5. ✓ Cleans up orphaned resources from previous deploys
6. ✓ Deploys all 4 stacks in dependency order
7. ✓ Starts Glue crawler for Athena schema
8. ✓ Configures QuickSight service role

### Single Stack Deployment

```bash
# Deploy only one stack
./deploy.sh --stack APIStack --region us-east-1

# Valid stack names:
# - APIStack
# - IntegrationStack
# - RekognitionStack
# - VisualizationStack
```

### Preview Changes (Dry-run)

```bash
# See what changes will be made
./deploy.sh --diff --region us-east-1
```

### Destroy All Stacks

```bash
./deploy.sh --destroy --region us-east-1
```

> ⚠️ **Note:** S3 image bucket and DynamoDB table have `RemovalPolicy.RETAIN` — they survive stack destruction for data safety.

### Clean Up Orphaned Resources

Before redeploying into an account with leftover resources:

```bash
./deploy.sh --cleanup --region us-east-1
```

Removes: Athena workgroup, Glue crawler, Glue database, QuickSight data source, SAR connector Lambda.

---

## 🔌 API Endpoints

### Upload Image

```bash
GET /prod/?url=<image_url>&name=<filename>
```

**Parameters:**
- `url` (required) — HTTPS URL of the image to download
- `name` (required) — Human-readable name for the image

**Example:**
```bash
curl "https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/?url=https://example.com/photo.jpg&name=photo.jpg"
```

**Response:**
```json
{
  "statusCode": 200,
  "body": "{\"message\": \"Image uploaded successfully\"}"
}
```

### List Classified Images

```bash
GET /prod/
```

**Example:**
```bash
curl "https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/"
```

**Response:**
```json
[
  {
    "image": "photo.jpg",
    "labels": ["Cat", "Animal", "Mammal"],
    "confidence": [95.5, 92.3, 88.1],
    "timestamp": "2026-07-01T22:30:00Z"
  }
]
```

### Save XML Payload

```bash
POST /save/
Content-Type: application/xml

<classifications>
  <image>photo.jpg</image>
  <labels>Cat, Animal</labels>
</classifications>
```

**Response:**
```json
{
  "statusCode": 200,
  "body": "{\"message\": \"XML saved to S3\"}"
}
```

---

## 📁 Project Structure

```
python/
├── app.py                          # CDK entry point — instantiates all 4 stacks
├── cdk.json                        # Context config (bucket names, prefixes, settings)
├── deploy.sh                       # Deployment orchestration script (main interface)
├── requirements.txt                # Python dependencies
├── scan_classifications.py         # DynamoDB utility (scan/seed)
│
├── api/                            # APIStack — Image Ingestion
│   ├── infrastructure.py           # Stack definition (API Gateway, Lambda, S3, SNS, SQS)
│   └── runtime/
│       ├── get_save_image.py       # TODO: Lambda handler (download + upload)
│       └── get_save_image_solution.py   # ✓ Reference implementation
│
├── recognition/                    # RekognitionStack — Classification
│   ├── infrastructure.py           # Stack definition
│   └── runtime/
│       ├── image_recognition.py    # TODO: Lambda (Rekognition + DynamoDB)
│       ├── image_recognition_solution.py
│       ├── list_images.py          # TODO: Lambda (scan DynamoDB)
│       └── list_images_solution.py
│
├── integration/                    # IntegrationStack — Downstream Forwarding
│   ├── infrastructure.py           # Stack definition
│   └── runtime/
│       ├── send_email.py           # TODO: Lambda (XML conversion + HTTP POST)
│       ├── send_email_solution.py
│       ├── SaveXMLLambda.py        # TODO: Lambda (receive + store XML)
│       └── SaveXMLLambda_solution.py
│
├── visualization/                  # VisualizationStack — Analytics
│   └── infrastructure.py           # Stack definition (no runtime code)
│
├── iam/                            # IAM Policies & Helper Scripts
│   ├── deployer-user-policy.json   # Aggregate of 3 policies below
│   ├── deployer-policy-1-infra.json
│   ├── deployer-policy-2-compute.json
│   ├── deployer-policy-3-analytics.json
│   ├── fix-cdk-bootstrap-trust.sh  # Fixes CDK bootstrap role trust
│   └── lambda-*-role.json          # Reference role definitions
│
└── cdk-outputs-*.json              # Stack outputs (auto-generated, gitignored)
```

### Convention

Every Lambda handler has a paired `*_solution.py` file with the reference implementation. Use these to learn best practices — **never modify solution files**.

---

## 🔧 Lambda Modules

### APIStack: `get_save_image.py`

**Purpose:** Download images from URLs and save to S3  
**Triggered by:** REST API `GET /?url=<url>&name=<name>`  
**Runtime:** 30 seconds  

**TODO Checklist:**
- [ ] Implement `get_file_from_url()` to download images with error handling
- [ ] Implement `upload_to_s3()` to save to the image bucket
- [ ] Handle HTTP errors gracefully (404, timeout, etc.)
- [ ] Return proper statusCode (200, 400, 502) with JSON body

**Key environment variables:**
- `BUCKET_NAME` — S3 image bucket
- `SNS_TOPIC_ARN` — image_uploaded topic (optional, S3 event handles it)

---

### RekognitionStack: `image_recognition.py`

**Purpose:** Run Rekognition DetectLabels and store results in DynamoDB  
**Triggered by:** SQS upload_queue (event source mapping)  
**Runtime:** 300 seconds (5 minutes)  

**TODO Checklist:**
- [ ] Parse SQS message to extract S3 bucket + key
- [ ] Call `rekognition.detect_labels()` with max 10 labels, 70% confidence threshold
- [ ] Write results to DynamoDB Classifications table (partition key: image name)
- [ ] Publish to SNS image_recognized topic
- [ ] Handle Rekognition errors (throttling, invalid image, etc.)

**Key environment variables:**
- `TABLE_NAME` — DynamoDB Classifications table
- `SNS_TOPIC_ARN` — image_recognized topic
- AWS IAM permissions: `rekognition:DetectLabels`, `dynamodb:PutItem`, `sns:Publish`

---

### RekognitionStack: `list_images.py`

**Purpose:** List all classified images from DynamoDB  
**Triggered by:** REST API `GET /`  
**Runtime:** 30 seconds  

**TODO Checklist:**
- [ ] Scan DynamoDB Classifications table
- [ ] Return JSON array of all classifications
- [ ] Handle pagination for large datasets
- [ ] Return proper statusCode (200) with JSON body

---

### IntegrationStack: `send_email.py`

**Purpose:** Convert Rekognition results to XML and POST to downstream endpoint  
**Triggered by:** SQS rekognized_queue (event source mapping)  
**Runtime:** 300 seconds (5 minutes)  

**TODO Checklist:**
- [ ] Parse SQS message (Rekognition result)
- [ ] Convert to XML format
- [ ] Retrieve downstream endpoint URL from SSM Parameter Store
- [ ] HTTP POST XML payload to endpoint
- [ ] Handle HTTP errors (timeout, 4xx, 5xx, etc.)

**Key environment variables:**
- `SSM_ENDPOINT_KEY` — SSM parameter storing the downstream endpoint URL

---

### IntegrationStack: `SaveXMLLambda.py`

**Purpose:** Receive XML payloads via API and store in S3  
**Triggered by:** REST API `POST /save/`  
**Runtime:** 30 seconds  

**TODO Checklist:**
- [ ] Parse incoming XML payload from request body
- [ ] Validate XML structure (basic sanity check)
- [ ] Generate timestamped S3 key
- [ ] Write to S3 XML bucket
- [ ] Return statusCode (200, 400, 500) with JSON response

**Key environment variables:**
- `XML_BUCKET_NAME` — S3 XML output bucket

---

## 🎯 Design Patterns

### Event-Driven Resilience

```
SQS Upload Queue ──(DLQ)──> SQS Upload DLQ ──> CloudWatch Alarm
SQS Rekognized Queue ──(DLQ)──> SQS Rekognized DLQ ──> CloudWatch Alarm
```

**Key principle:** SQS visibility timeout ≥ 6× Lambda timeout
- Upload queue: 360s visibility (Lambda timeout: 30s)
- Rekognized queue: 1800s visibility (Lambda timeout: 300s)

### Boto3 Connection Reuse

```python
# ✓ GOOD: Instantiate outside handler
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

def handler(event, context):
    # Reuse connections across invocations
    s3_client.put_object(...)
    table.put_item(...)
```

### Least-Privilege IAM

Each Lambda has its own role with **only** the permissions it needs:
- `ImageGetAndSaveLambda` — S3 PutObject only
- `image_recognition` — Rekognition DetectLabels + DynamoDB PutItem + SNS Publish
- `send_email` — SSM GetParameter + HTTP (no AWS API needed)
- `SaveXMLLambda` — S3 PutObject only

### Configuration as Code

All runtime config flows through `cdk.json` context:

```json
{
  "context": {
    "asset_bucket": "my-bucket",
    "image_bucket_prefix": "sagemaker",
    "layer_zip_key": "requests_layer3_11.zip",
    "quicksight_user": "my-user"
  }
}
```

Lambda receives config via **environment variables** (set by CDK):

```python
import os
BUCKET_NAME = os.getenv('BUCKET_NAME')
TABLE_NAME = os.getenv('TABLE_NAME')
```

---

## 🔐 IAM & Security

### Deploy User Permissions

Attach `iam/deployer-user-policy.json` to your IAM user. It includes three sub-policies:

| Policy | Coverage |
|--------|----------|
| `deployer-policy-1-infra.json` | S3, CloudFormation, CDK bootstrap, SSM |
| `deployer-policy-2-compute.json` | Lambda, API Gateway, SQS, SNS, DynamoDB, IAM |
| `deployer-policy-3-analytics.json` | Athena, Glue, QuickSight, Rekognition |

### S3 Bucket Security

All buckets configured with:
- ✓ Block all public access (`BLOCK_ALL`)
- ✓ S3-managed encryption (default)
- ✓ Enforce SSL (HTTPS only)
- ✓ Versioning enabled (except result/spill buckets)
- ✓ Retention policy (RETAIN on destroy)

### DynamoDB Fine-Tuning

- **Billing:** On-demand (auto-scales)
- **Partition key:** `image` (string)
- **Retention:** RETAIN on destroy (data safety)
- **Encryption:** AWS managed

### Rekognition Best Practices

- Max 10 labels per image (prevents noise)
- 70% confidence threshold (filters low-quality detections)
- Error handling for throttling (boto3 auto-retries with exponential backoff)

---

## 📊 Monitoring & Debugging

### CloudWatch Logs

```bash
# Tail real-time logs for a Lambda
aws logs tail /aws/lambda/ImageGetAndSaveLambda --follow --region us-east-1

# View logs for all stacks
aws logs tail /aws/lambda/ --follow --region us-east-1
```

### DynamoDB Metrics

```bash
# Scan the Classifications table
python scan_classifications.py --region us-east-1

# Seed test data
python scan_classifications.py --seed --region us-east-1
```

### SQS Dead-Letter Queues

```bash
# Check for failed messages
aws sqs receive-message \
  --queue-url <dlq-url> \
  --region us-east-1 \
  --max-number-of-messages 10
```

### Athena Query Status

```bash
# Check Athena query execution
aws athena list-query-executions --region us-east-1
```

### API Gateway Metrics

```bash
# View CloudFormation stack status
aws cloudformation describe-stacks \
  --stack-name APIStack \
  --query 'Stacks[0].StackStatus' \
  --region us-east-1
```

---

## 🐛 Troubleshooting

### Image Upload Returns 502

**Cause:** Lambda timeout or URL not accessible  
**Fix:**
```bash
# Check Lambda logs
aws logs tail /aws/lambda/ImageGetAndSaveLambda --follow --region us-east-1

# Ensure URL is HTTPS and publicly accessible
curl https://example.com/image.jpg
```

### DynamoDB Records Not Appearing

**Cause:** Rekognition Lambda not triggered or failed  
**Fix:**
```bash
# Check Rekognition Lambda logs
aws logs tail /aws/lambda/image_recognition --follow --region us-east-1

# Verify SQS event source mapping exists
aws lambda list-event-source-mappings --function-name image_recognition --region us-east-1

# Check SQS queue for messages
aws sqs get-queue-attributes \
  --queue-url <upload-queue-url> \
  --attribute-names ApproximateNumberOfMessages \
  --region us-east-1
```

### QuickSight Dashboard Missing Data

**Cause:** Glue crawler not run or Athena connector not deployed  
**Fix:**
```bash
# Run Glue crawler manually
aws glue start-crawler --name dynamodb-classifications-crawler --region us-east-1

# Wait 2-3 minutes, then retry QuickSight query
```

### VisualizationStack Deploy Fails

**Cause:** RekognitionStack not deployed first (missing DynamoDB table)  
**Fix:**
```bash
# Deploy RekognitionStack first
./deploy.sh --stack RekognitionStack --region us-east-1

# Wait for completion, then deploy VisualizationStack
./deploy.sh --stack VisualizationStack --region us-east-1

# Or override table name
cdk deploy VisualizationStack -c dynamodb_table_name=Classifications --region us-east-1
```

### S3 Bucket Event Notification Missing

**Cause:** Image bucket has RETAIN policy; CDK can't re-add notification on redeploy  
**Fix:**
```bash
# Add notification manually
aws s3api put-bucket-notification-configuration \
  --bucket sagemaker-us-east-1-<account> \
  --notification-configuration '{
    "TopicConfigurations": [{
      "TopicArn": "<image-uploaded-topic-arn>",
      "Events": ["s3:ObjectCreated:Put"]
    }]
  }' \
  --region us-east-1

# Get topic ARN from:
cat cdk-outputs-APIStack.json
```

---

## 🎓 Learning Objectives

### Serverless Concepts

- [ ] Understand event-driven architecture (SNS/SQS)
- [ ] Learn Lambda execution models (synchronous vs. event-driven)
- [ ] Implement resilience patterns (DLQs, retries, timeouts)
- [ ] Configure least-privilege IAM roles

### AWS Services

- [ ] Deploy infrastructure with AWS CDK (Python)
- [ ] Integrate multiple AWS services (Lambda, S3, DynamoDB, SNS, SQS, Rekognition, Athena)
- [ ] Use boto3 for AWS SDK operations
- [ ] Configure CloudWatch monitoring and alarms

### Design Patterns

- [ ] Implement event-driven data pipelines
- [ ] Handle asynchronous workflows
- [ ] Design systems for resilience and monitoring
- [ ] Manage complex cross-stack dependencies

### Python Best Practices

- [ ] Write Lambda handlers following AWS conventions
- [ ] Use environment variables for configuration
- [ ] Implement structured logging (logging module)
- [ ] Handle errors gracefully with proper HTTP status codes

---

## 📚 Additional Resources

### AWS Documentation
- [AWS Lambda Developer Guide](https://docs.aws.amazon.com/lambda/)
- [Amazon Rekognition User Guide](https://docs.aws.amazon.com/rekognition/)
- [AWS CDK Python Reference](https://docs.aws.amazon.com/cdk/latest/guide/work_with_cdk_python.html)
- [Amazon DynamoDB Developer Guide](https://docs.aws.amazon.com/dynamodb/)

### Useful AWS Console Links

| Service | Link |
|---------|------|
| CloudFormation Stacks | `https://us-east-1.console.aws.amazon.com/cloudformation/home#/stacks` |
| Lambda Functions | `https://us-east-1.console.aws.amazon.com/lambda/home#/functions` |
| DynamoDB Tables | `https://us-east-1.console.aws.amazon.com/dynamodbv2/home#tables` |
| S3 Buckets | `https://s3.console.aws.amazon.com/s3/home` |
| CloudWatch Logs | `https://us-east-1.console.aws.amazon.com/logs/home` |
| API Gateway | `https://us-east-1.console.aws.amazon.com/apigateway/home` |
| Athena | `https://us-east-1.console.aws.amazon.com/athena/home` |
| Glue Crawlers | `https://us-east-1.console.aws.amazon.com/glue/home` |
| QuickSight | `https://us-east-1.quicksight.aws.amazon.com/` |

---

## 🤝 Contributing

This is a learning project. Contributions are welcome! Feel free to:
- Report issues
- Submit improvements to Lambda handlers
- Enhance documentation
- Add test cases

---

## 📝 License

This project is provided as-is for educational purposes.

---

## 🙋 Support

### Stuck?

1. **Check CloudWatch Logs** — Most issues are visible here
2. **Review Lambda Environment Variables** — Ensure all config is correct
3. **Verify IAM Permissions** — Use IAM Access Analyzer
4. **Check SQS Queues** — Are messages being delivered?
5. **Test Manually** — Use AWS CLI to test individual services

### Questions?

Refer to the **Troubleshooting** section above or consult AWS documentation.

---

**Last Updated:** July 2026  
**Python Version:** 3.11  
**AWS CDK Version:** 2.118.0  
**Status:** Production-Ready
