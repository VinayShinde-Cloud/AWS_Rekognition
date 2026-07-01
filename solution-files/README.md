# Cloudage Image Rekognition

An AWS-based image processing pipeline built with Python and AWS CDK. The system accepts image URLs via a REST API, runs Amazon Rekognition label detection on each image, persists the results in DynamoDB, forwards them as XML to a downstream endpoint, and visualises the data in Amazon QuickSight via Athena federated queries.

This project is structured as a workshop — each Lambda module contains `TODO` comments and a paired `*_solution.py` reference implementation.

---

## Architecture

```
User → API Gateway (APIStack)
         └─ ImageGetAndSaveLambda → S3 (image bucket)
                                      └─ SNS → SQS (upload queue)
                                                 └─ image_recognition Lambda (RekognitionStack)
                                                      ├─ Rekognition DetectLabels
                                                      ├─ DynamoDB (Classifications table)
                                                      └─ SNS → SQS (rekognized queue)
                                                                  └─ IntegrationLambda (IntegrationStack)
                                                                       ├─ SSM (endpoint URL)
                                                                       └─ SaveXMLLambda via API Gateway

DynamoDB → Athena federated query (VisualizationStack)
             └─ Glue Data Catalog → QuickSight
```

### Stacks

| Stack | Domain | Key Resources |
|-------|--------|---------------|
| **APIStack** | Image ingestion | API Gateway, `ImageGetAndSaveLambda`, S3 image bucket, SNS topic, SQS upload queue |
| **IntegrationStack** | Downstream forwarding | SNS topic, SQS rekognized queue, `IntegrationLambda`, `SaveXMLLambda`, API Gateway, SSM parameter, S3 XML bucket |
| **RekognitionStack** | Image classification | `image_recognition` Lambda, `ListImagesLambda`, DynamoDB Classifications table, API Gateway |
| **VisualizationStack** | Analytics | Athena DynamoDB connector (SAR), Glue crawler, Athena workgroup, QuickSight data source |

### Data Flow

1. Client calls `GET /?url=<image_url>&name=<filename>` on the upload API.
2. `ImageGetAndSaveLambda` downloads the image and writes it to S3.
3. S3 fires an `ObjectCreated:Put` event → SNS → SQS upload queue.
4. `image_recognition` Lambda polls the queue, calls `rekognition:DetectLabels` (max 10 labels, 70% min confidence), writes results to DynamoDB, and publishes to the rekognized SNS topic.
5. `IntegrationLambda` polls the rekognized queue, converts the result to XML, and POSTs it to the `SaveXMLLambda` endpoint (URL stored in SSM Parameter Store).
6. `SaveXMLLambda` saves the XML payload to S3 with a timestamped key.
7. QuickSight queries DynamoDB via Athena federated queries (Athena DynamoDB connector → Glue Data Catalog).

---

## Project Structure

```
python/
├── app.py                          # CDK app entry point — instantiates all 4 stacks
├── cdk.json                        # CDK context config (bucket names, prefixes, flags)
├── deploy.sh                       # Main deploy/destroy/diff script
├── requirements.txt                # Runtime deps (aws-cdk-lib, constructs, boto3)
├── requirements-dev.txt            # Dev deps
├── scan_classifications.py         # CLI utility to scan/seed the DynamoDB table
├── requests_layer3_11.zip          # Pre-built Lambda layer (requests lib for Python 3.11)
│
├── api/                            # APIStack
│   ├── infrastructure.py
│   └── runtime/
│       ├── get_save_image.py       # Lambda: downloads image from URL, saves to S3
│       └── get_save_image_solution.py
│
├── recognition/                    # RekognitionStack
│   ├── infrastructure.py
│   └── runtime/
│       ├── image_recognition.py    # Lambda: runs Rekognition, writes to DynamoDB, triggers SNS
│       ├── image_recognition_solution.py
│       ├── list_images.py          # Lambda: scans DynamoDB, returns all classified images
│       └── list_images_solution.py
│
├── integration/                    # IntegrationStack
│   ├── infrastructure.py
│   └── runtime/
│       ├── send_email.py           # Lambda: converts rekognition results to XML, POSTs to endpoint
│       ├── send_email_solution.py
│       └── SaveXMLLambda.py        # Lambda: receives XML POST, saves to S3
│
├── visualization/                  # VisualizationStack
│   └── infrastructure.py
│
├── iam/                            # IAM policy documents and helper scripts
│   ├── deployer-user-policy.json   # Minimum permissions for the deploy IAM user
│   ├── fix-cdk-bootstrap-trust.sh  # Patches CDK bootstrap role trust policies
│   └── *.json                      # Per-Lambda IAM role definitions (reference)
│
└── cdk-outputs-*.json              # Stack outputs written by deploy.sh (gitignored)
```

> **Convention:** every Lambda has a `*_solution.py` counterpart with the reference implementation. Never modify solution files.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11 |
| IaC | AWS CDK v2 (`aws-cdk-lib==2.118.0`) |
| AWS SDK | boto3 `1.34.144` |
| Lambda layer | `requests` library (`requests_layer3_11.zip`) |
| Image classification | Amazon Rekognition `DetectLabels` |
| Storage | S3 (images, XML payloads, Athena results/spill) |
| Database | DynamoDB (Classifications table, partition key: `image`) |
| Messaging | SNS + SQS (all queues have DLQs + CloudWatch alarms) |
| Config | SSM Parameter Store (third-party endpoint URL) |
| Analytics | Athena federated query → Glue Data Catalog → QuickSight |
| Observability | CloudWatch (Lambda error alarms, DLQ alarms, API Gateway metrics) |

---

## Prerequisites

- Python 3.11
- Node.js (for AWS CDK CLI): `npm install -g aws-cdk`
- AWS CLI v2 configured: `aws configure`
- An AWS account with QuickSight subscribed (required for VisualizationStack)

---

## Setup

All commands run from the `python/` directory.

```bash
cd python

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## CDK Context Keys

Configured in `cdk.json`. Override at deploy time with `-c key=value`.

| Key | Default | Purpose |
|-----|---------|---------|
| `asset_bucket` | `rekognition-784055307907` | S3 bucket holding the Lambda layer zip (account-specific) |
| `image_bucket_prefix` | `sagemaker` | Prefix for the image bucket (`<prefix>-<region>-<account>`) |
| `layer_zip_key` | `requests_layer3_11.zip` | S3 key for the requests layer |
| `quicksight_user` | `Vinay-AI` | QuickSight username for data source ownership |
| `image_bucket_exists` | `"false"` | Set automatically by `deploy.sh`; controls import vs create for the image bucket |

---

## Deployment

### Deploy all stacks

```bash
./deploy.sh --region us-east-1
```

`deploy.sh` handles everything automatically:
1. Verifies AWS CLI, CDK, and Python venv
2. Runs `cdk bootstrap` if not already done
3. Creates the asset S3 bucket and uploads the Lambda layer zip if needed
4. Detects whether the image bucket already exists and sets `image_bucket_exists` accordingly
5. Cleans up orphaned named resources from previous deployments
6. Deploys all 4 stacks in dependency order
7. Starts the Glue crawler to populate the Athena schema
8. Attaches `AWSQuicksightAthenaAccess` to the QuickSight service role

### Deploy a single stack

```bash
./deploy.sh --stack APIStack --region us-east-1
# Valid: APIStack, IntegrationStack, RekognitionStack, VisualizationStack
```

### Preview changes without deploying

```bash
./deploy.sh --diff --region us-east-1
```

### Destroy all stacks

```bash
./deploy.sh --destroy --region us-east-1
```

> Resources with `RemovalPolicy.RETAIN` (S3 image bucket, DynamoDB Classifications table) are **not** deleted on destroy.

### Clean up orphaned named resources

Run this before redeploying into an account that has leftover resources from a previous deployment:

```bash
./deploy.sh --cleanup --region us-east-1
```

Removes: Athena workgroup, Athena data catalog, Glue crawler, Glue database, QuickSight data source, SAR connector Lambda.

---

## Stack Deployment Order

The stacks have explicit dependencies and must be deployed in this order:

```
1. APIStack          — creates S3 image bucket, SQS upload queue, SNS topic
2. IntegrationStack  — creates SNS rekognized topic, SQS rekognized queue, SaveXMLLambda
3. RekognitionStack  — needs SQS ARN (APIStack) + SNS ARN (IntegrationStack)
4. VisualizationStack — needs DynamoDB table name from RekognitionStack outputs
```

`deploy.sh` handles this order automatically. The `VisualizationStack` reads the DynamoDB table name from `cdk-outputs-RekognitionStack.json` at synth time — deploy `RekognitionStack` first if deploying stacks individually.

---

## Post-Deployment

### Start the Glue crawler

Run once after deploying `VisualizationStack` to populate the Glue Data Catalog schema (required for Athena queries from QuickSight):

```bash
aws glue start-crawler --name dynamodb-classifications-crawler --region us-east-1
```

`deploy.sh` runs this automatically on a full deploy.

### Seed test data

```bash
# Seed sample classification records into DynamoDB
python scan_classifications.py --seed --region us-east-1

# Scan and print all records
python scan_classifications.py --region us-east-1
```

### Test the upload API

```bash
# Get the API endpoint from the stack outputs
cat cdk-outputs-APIStack.json

# Upload an image by URL (replace with actual API ID)
curl "https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/?url=https://example.com/photo.jpg&name=photo.jpg"
```

### List classified images

```bash
cat cdk-outputs-RekognitionStack.json
curl "https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/"
```

---

## IAM

### Deployer permissions

Attach `iam/deployer-user-policy.json` to the IAM user running `cdk deploy`. The policy is split across three files for readability:

| File | Covers |
|------|--------|
| `deployer-policy-1-infra.json` | S3, SSM, CloudFormation, CDK bootstrap |
| `deployer-policy-2-compute.json` | Lambda, API Gateway, SQS, SNS, DynamoDB |
| `deployer-policy-3-analytics.json` | Athena, Glue, QuickSight, Rekognition |

### Fix CDK bootstrap trust policies

Run once after `cdk bootstrap` to eliminate "could not assume role" warnings:

```bash
./iam/fix-cdk-bootstrap-trust.sh
```

`deploy.sh` runs this automatically on every deploy.

### Athena DynamoDB connector Lambda role

The SAR connector requires these four AWS managed policies (confirmed from production):

- `service-role/AWSLambdaBasicExecutionRole`
- `AmazonDynamoDBFullAccess`
- `AmazonS3FullAccess`
- `service-role/AWSQuicksightAthenaAccess`

CDK attaches these automatically via `ConnectorLambdaRole` in `visualization/infrastructure.py`.

### QuickSight service role

`AWSQuicksightAthenaAccess` must be attached to `aws-quicksight-service-role-v0`. `deploy.sh` does this automatically. To attach manually:

```bash
aws iam attach-role-policy \
  --role-name aws-quicksight-service-role-v0 \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSQuicksightAthenaAccess
```

---

## Key Design Decisions

- **SQS visibility timeout** — set to ≥ 6× the Lambda timeout to prevent duplicate processing. Upload queue: 360s (Lambda timeout 30s). Rekognized queue: 1800s (Lambda timeout 300s).
- **DLQs** — every SQS queue has a dead-letter queue with a CloudWatch alarm on `ApproximateNumberOfMessagesVisible`.
- **S3 buckets** — all buckets use `BLOCK_ALL` public access, S3-managed encryption, SSL enforcement, and `RETAIN` removal policy (except Athena spill/results buckets which use `DESTROY` with a lifecycle rule).
- **Cross-stack values** — passed as plain strings (constructor parameters), not CDK tokens, to avoid CloudFormation export locks.
- **boto3 clients** — instantiated at module level (outside the handler) for Lambda connection reuse.
- **Logging** — `logging` module with `logger.setLevel(logging.INFO)`; no bare `print()` in Lambda handlers.
- **CDK context** — all runtime config (bucket names, prefixes) flows through `cdk.json` context keys; never hardcoded.

---

## Known Issues & Fixes

### S3 bucket event notification missing after redeploy

The image S3 bucket has `RemovalPolicy.RETAIN` — it survives stack destroy. On redeploy, CDK imports the existing bucket but cannot re-add the event notification via CloudFormation. `deploy.sh` detects this and sets `image_bucket_exists=true`, which grants the SNS topic policy instead.

If the notification is still missing after deploy, add it manually:

```bash
aws s3api put-bucket-notification-configuration \
  --bucket sagemaker-us-east-1-784055307907 \
  --notification-configuration '{
    "TopicConfigurations": [{
      "TopicArn": "<uploaded_image_topic_arn>",
      "Events": ["s3:ObjectCreated:Put"]
    }]
  }' \
  --region us-east-1
```

Get the topic ARN from `cdk-outputs-APIStack.json`.

### Athena workgroup delete fails on destroy

AWS returns 400 if the workgroup contains saved queries. `deploy.sh --destroy` runs `cleanup_orphaned_resources` first, which uses `--recursive-delete-option` to force-delete the workgroup.

### image_recognition Lambda event source mapping missing

CDK generates a random function name if `function_name` is not set. If the event source mapping is missing after deploy:

```bash
aws lambda create-event-source-mapping \
  --function-name <actual-function-name> \
  --event-source-arn <uploaded_image_queue_arn> \
  --batch-size 1 \
  --region us-east-1
```

Get the function name from `aws lambda list-functions --region us-east-1`.

### VisualizationStack fails if RekognitionStack not deployed first

`app.py` reads the DynamoDB table name from `cdk-outputs-RekognitionStack.json`. If that file doesn't exist, the table name will be empty and the stack will fail. Always deploy `RekognitionStack` before `VisualizationStack`, or override with:

```bash
cdk deploy VisualizationStack -c dynamodb_table_name=<table-name>
```

---

## Useful Console Links

AWS Console links for region `us-east-1` and account `784055307907`.

| Service | URL |
|---------|-----|
| CloudFormation | `https://us-east-1.console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks` |
| Lambda | `https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions` |
| DynamoDB | `https://us-east-1.console.aws.amazon.com/dynamodbv2/home?region=us-east-1#tables` |
| Glue Crawlers | `https://us-east-1.console.aws.amazon.com/glue/home?region=us-east-1#/catalog/crawlers` |
| Athena | `https://us-east-1.console.aws.amazon.com/athena/home?region=us-east-1` |
| QuickSight | `https://us-east-1.quicksight.aws.amazon.com/` |
