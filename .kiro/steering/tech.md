# Technology Stack

## Runtime Environment

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11 | Lambda handler language and CDK app |
| boto3 | ≥1.34.144 | AWS SDK for Python |
| botocore | ≥1.34.144 | boto3 dependency |
| requests | (from layer) | HTTP downloads in Lambda |

## Infrastructure-as-Code

| Component | Version | Purpose |
|-----------|---------|---------|
| AWS CDK | v2 (2.118.0) | Infrastructure orchestration |
| constructs | 10.x | CDK core constructs and patterns |
| aws-cdk-lib | Latest | CDK library with AWS service constructs |
| AWS CLI v2 | latest | Account/region management, manual operations |

## AWS Services Used

| Service | Purpose | Key Usage |
|---------|---------|-----------|
| API Gateway | REST endpoints | Image upload (`GET /?url=&name=`), list classifications |
| Lambda | Event handlers | 6 functions: image save, recognize, list, send XML, save XML, Athena connector |
| S3 | Object storage | Images, XML payloads, Athena results/spill buckets |
| DynamoDB | NoSQL database | Classifications table (partition key: `image`, on-demand billing) |
| SNS | Event publishing | Image uploaded, image recognized topics |
| SQS | Async queues | upload_queue (API→Rekognition), rekognized_queue (Rekognition→Integration) |
| Rekognition | ML classification | DetectLabels API (max 10 labels, 70% confidence) |
| Athena | Federated queries | Queries on DynamoDB via SAR connector |
| Glue | Data catalog | Schema discovery for DynamoDB via crawler |
| QuickSight | Visualization | Dashboards and insights from DynamoDB data |
| SSM Parameter Store | Configuration | Downstream HTTP endpoint URL (external system) |
| CloudWatch | Observability | Logs, metrics, alarms on DLQs and Lambda errors |
| IAM | Access control | Roles with least-privilege policies per Lambda |

## Lambda Layer

- **requests_layer3_11.zip** — Pre-built requests library for Python 3.11
- Stored in S3 asset bucket (key: `requests_layer3_11.zip`)
- Deployed via CDK `LayerVersion` construct
- Reduces cold start time by ~1.5s vs pip install at runtime

## Build & Deployment

### Prerequisites

```
✓ Python 3.11
✓ Node.js (for AWS CDK CLI) — install with: npm install -g aws-cdk
✓ AWS CLI v2 configured — verify with: aws sts get-caller-identity
✓ AWS account with QuickSight subscription (required for VisualizationStack)
```

### Setup

```bash
cd solution-files/python
python3 -m venv .venv

# Activate virtual environment:
# On Linux/Mac:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

pip install -r requirements.txt
```

### Common Commands

All commands run from `solution-files/python/` directory.

| Command | Purpose |
|---------|---------|
| `./deploy.sh` | Deploy all 4 stacks in dependency order (handles bootstrap, assets, cleanup) |
| `./deploy.sh --stack APIStack` | Deploy a single stack (APIStack, IntegrationStack, RekognitionStack, VisualizationStack) |
| `./deploy.sh --diff` | Preview CloudFormation changes without deploying |
| `./deploy.sh --destroy` | Destroy all stacks (respects RETAIN policies on S3 and DynamoDB) |
| `./deploy.sh --cleanup` | Remove orphaned resources before redeployment (Athena workgroup, Glue, QuickSight, etc.) |
| `python scan_classifications.py --seed --region us-east-1` | Seed sample data in DynamoDB |
| `python scan_classifications.py --region us-east-1` | Scan and print all DynamoDB records |
| `cdk synth` | Generate CloudFormation templates (JSON output in `cdk.out/`) |
| `cdk bootstrap aws://<account>/<region>` | Initialize CDK bootstrap stack (run once per account/region) |

### Deployment Order & Dependencies

Stacks must deploy in this order (handled automatically by `deploy.sh`):

```
1. APIStack
   └─ Creates: S3 image bucket, SQS upload queue, SNS image_uploaded topic
   
2. IntegrationStack
   └─ Creates: SNS image_recognized topic, SQS rekognized queue, SaveXMLLambda
   
3. RekognitionStack
   └─ Consumes: upload_queue (APIStack), image_recognized topic (IntegrationStack)
   └─ Creates: DynamoDB Classifications table, image_recognition Lambda
   
4. VisualizationStack
   └─ Reads: DynamoDB table name from RekognitionStack outputs (cdk-outputs-RekognitionStack.json)
   └─ Creates: Athena connector, Glue crawler, QuickSight data source
```

## CDK Context Configuration

File: `cdk.json` (can override with `-c key=value` at deploy time)

| Key | Default | Purpose |
|-----|---------|---------|
| `asset_bucket` | `cloudage-resources-715` | S3 bucket containing Lambda layer zip |
| `image_bucket_prefix` | `sagemaker` | Prefix for image bucket: `<prefix>-<region>-<account>` |
| `layer_zip_key` | `requests_layer3_11.zip` | S3 key within asset_bucket for layer zip |
| `quicksight_user` | `gen-ai-user` | QuickSight username who owns data sources |
| `image_bucket_exists` | auto-set by deploy.sh | Controls import vs create for image bucket |

Override example:
```bash
./deploy.sh -c asset_bucket=my-bucket -c image_bucket_prefix=my-images
```

## SQS Queue Configuration

All SQS queues follow this pattern for reliability:

| Queue | Visibility Timeout | DLQ Max Receives | Lambda Timeout |
|-------|-------------------|------------------|----------------|
| upload_queue | 360s | 3 | 30s |
| rekognized_queue | 1800s | 3 | 300s |

Rule: Visibility timeout ≥ 6 × Lambda timeout (prevents duplicate processing if Lambda fails mid-execution).

## Code Organization

```
python/
├── app.py                         # CDK app entry — imports and instantiates all stacks
├── cdk.json                       # Context config (bucket names, prefixes, etc.)
├── deploy.sh                      # Deployment orchestration script
├── requirements.txt               # Python dependencies
├── scan_classifications.py        # DynamoDB utility for testing
├── api/                           # APIStack
│   ├── infrastructure.py          # Stack definition (API Gateway, Lambda, S3, SNS, SQS)
│   └── runtime/
│       ├── get_save_image.py      # Lambda handler (download + save image)
│       └── get_save_image_solution.py  # Reference implementation
├── recognition/                   # RekognitionStack
│   ├── infrastructure.py
│   └── runtime/
│       ├── image_recognition.py       # Lambda: Rekognition + DynamoDB
│       ├── image_recognition_solution.py
│       ├── list_images.py             # Lambda: DynamoDB scan
│       └── list_images_solution.py
├── integration/                   # IntegrationStack
│   ├── infrastructure.py
│   └── runtime/
│       ├── send_email.py              # Lambda: XML conversion + HTTP POST
│       ├── send_email_solution.py
│       ├── SaveXMLLambda.py           # Lambda: Save XML to S3
│       └── SaveXMLLambda_solution.py
├── visualization/                 # VisualizationStack
│   └── infrastructure.py          # Athena + Glue + QuickSight (no runtime code)
├── iam/                           # IAM policy reference files
│   ├── deployer-user-policy.json      # Aggregate policy (split across 3 files)
│   ├── deployer-policy-1-infra.json
│   ├── deployer-policy-2-compute.json
│   ├── deployer-policy-3-analytics.json
│   ├── fix-cdk-bootstrap-trust.sh
│   └── lambda-*-role.json             # Per-Lambda role definitions
├── cdk-outputs-*.json             # Stack outputs (auto-generated, gitignored)
└── .venv/                         # Virtual environment (gitignored)
```

## Lambda Handler Code Style

Every Lambda handler follows this structure:

```python
import os
import json
import logging
import boto3
import botocore.exceptions

# Module-level logger and boto3 clients (reused across invocations)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

# Environment variables read at import time
BUCKET_NAME = os.getenv('BUCKET_NAME')
TABLE_NAME = os.getenv('TABLE_NAME')

def handler(event, context):
    """Handle Lambda event. Return dict with statusCode and body."""
    try:
        # TODO: Implement logic
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'success'})
        }
    except Exception as e:
        logger.error(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

### Key Conventions

- **Clients at module level** — boto3 clients created outside handler for connection reuse
- **Environment variables** — all config passed as Lambda env vars (set in infrastructure.py)
- **Logging** — use `logger.info()`, `logger.error()`, never `print()`
- **Error handling** — catch specific exceptions (e.g., `botocore.exceptions.ClientError`), log, and return error response
- **JSON responses** — always return dict with `statusCode` and `body` (API Gateway format)
- **No hardcoding** — all config (bucket names, table names, URLs) come from env vars or cdk.json

## CDK Stack Patterns

### S3 Bucket Patterns

```python
# Secure defaults for all buckets
bucket = s3.Bucket(
    self, "MyBucket",
    bucket_name="my-name",
    removal_policy=RemovalPolicy.RETAIN,        # Keep on destroy
    block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
    encryption=s3.BucketEncryption.S3_MANAGED,
    versioned=True,
    enforce_ssl=True
)
```

### Lambda Function Patterns

```python
# Always include timeout, role, and description
lambda_func = lambda_.Function(
    self, "MyLambda",
    function_name="MyLambda",
    runtime=lambda_.Runtime.PYTHON_3_11,
    layers=[requests_layer],
    role=my_role,
    code=lambda_.Code.from_asset("module/runtime"),
    handler="module_name.handler",
    timeout=Duration.seconds(30),
    environment={"BUCKET_NAME": bucket.bucket_name},
    description="Description of what this Lambda does"
)
```

### SQS Queue with DLQ Pattern

```python
dlq = sqs.Queue(self, "MyDLQ", retention_period=Duration.days(14))
queue = sqs.Queue(
    self, "MyQueue",
    visibility_timeout=Duration.seconds(360),  # 6× Lambda timeout
    dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=3, queue=dlq)
)
# Add alarm
dlq.metric_approximate_number_of_messages_visible().create_alarm(...)
```

## Post-Deployment Tasks

After successful deployment:

1. **Start Glue crawler** (populates schema for Athena):
   ```bash
   aws glue start-crawler --name dynamodb-classifications-crawler --region <region>
   ```

2. **Seed test data** (optional):
   ```bash
   python scan_classifications.py --seed --region <region>
   ```

3. **Test upload endpoint**:
   ```bash
   # Get API URL from cdk-outputs-APIStack.json
   curl "https://<api-id>.execute-api.<region>.amazonaws.com/prod/?url=https://example.com/photo.jpg&name=photo.jpg"
   ```

## Troubleshooting Commands

| Issue | Command |
|-------|---------|
| View all Lambda functions | `aws lambda list-functions --region <region>` |
| Tail Lambda logs (real-time) | `aws logs tail /aws/lambda/<function-name> --follow --region <region>` |
| View SQS DLQ messages | `aws sqs receive-message --queue-url <dlq-url> --region <region>` |
| Scan DynamoDB table | `python scan_classifications.py --region <region>` |
| View CloudFormation events | `aws cloudformation describe-stacks --query 'Stacks[*].[StackName,StackStatus]' --region <region>` |
| Get stack outputs | `aws cloudformation describe-stacks --stack-name <stack-name> --query 'Stacks[0].Outputs' --region <region>` |
| Check Athena query status | `aws athena list-query-executions --region <region>` |

## Known Workarounds

1. **Image bucket event notification missing after redeploy**: `deploy.sh` sets `image_bucket_exists=true` on redeploy, which uses SNS policy grant instead of CloudFormation event notification.

2. **image_recognition Lambda event source mapping not created**: If missing after deploy, manually create:
   ```bash
   aws lambda create-event-source-mapping --function-name ImageRecognition \
     --event-source-arn <upload_queue_arn> --batch-size 1 --region <region>
   ```

3. **VisualizationStack fails if RekognitionStack not deployed**: The stack reads `cdk-outputs-RekognitionStack.json` at synth time. Deploy stacks in order or override:
   ```bash
   cdk deploy VisualizationStack -c dynamodb_table_name=<table-name>
   ```
