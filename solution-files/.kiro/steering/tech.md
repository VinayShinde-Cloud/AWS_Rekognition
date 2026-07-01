# Tech Stack

## Language & Runtime
- Python 3.11 (Lambda functions and CDK app)
- AWS CDK v2 (`aws-cdk-lib==2.118.0`, `constructs>=10.0.0,<11.0.0`)
- boto3 `1.34.144`

## AWS Services Used
- **API Gateway** — REST APIs for image upload and image listing
- **Lambda** — all compute; Python 3.11 runtime
- **S3** — image storage, XML payload storage, Athena spill/results buckets
- **SQS** — decouples upload events and rekognition results; all queues have DLQs
- **SNS** — fan-out for S3 upload events and rekognition completion notifications
- **Amazon Rekognition** — label detection (`DetectLabels`, max 10 labels, 70% min confidence)
- **DynamoDB** — stores classification results (partition key: `image`)
- **SSM Parameter Store** — stores third-party endpoint URL
- **Athena** — federated queries over DynamoDB via the DynamoDB connector
- **Glue** — data catalog and crawler for DynamoDB schema inference
- **QuickSight** — visualisation layer connected via Athena data source
- **CloudWatch** — Lambda error alarms, DLQ alarms, API Gateway metrics

## Lambda Layer
- `requests_layer3_11.zip` — pre-built `requests` library for Python 3.11
- Stored in the asset S3 bucket (`asset_bucket` context key in `cdk.json`)

## Infrastructure as Code
- AWS CDK (Python) — all infrastructure defined in `*/infrastructure.py` files
- CDK context values in `cdk.json` (override with `-c key=value` at deploy time)
- Stack outputs written to `cdk-outputs-<StackName>.json` by `deploy.sh`

## Common Commands

### Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Deploy (all stacks)
```bash
./deploy.sh
```

### Deploy a single stack
```bash
./deploy.sh --stack APIStack
# Valid stacks: APIStack, IntegrationStack, RekognitionStack, VisualizationStack
```

### Preview changes
```bash
./deploy.sh --diff
```

### Destroy all stacks
```bash
./deploy.sh --destroy
```

### Synthesise CDK templates (validate without deploying)
```bash
cdk synth
```

### Scan / seed DynamoDB test data
```bash
python scan_classifications.py --seed --region <region>
python scan_classifications.py --region <region>
```

### Start Glue crawler (run after deploying VisualizationStack)
```bash
aws glue start-crawler --name dynamodb-classifications-crawler
```

## Key CDK Context Keys (`cdk.json`)
| Key | Default | Purpose |
|-----|---------|---------|
| `asset_bucket` | `cloudage-resources-204` | S3 bucket holding the Lambda layer zip |
| `image_bucket_prefix` | `sagemaker` | Prefix for the image bucket (`<prefix>-<region>-<account>`) |
| `layer_zip_key` | `requests_layer3_11.zip` | S3 key for the requests layer |
| `quicksight_user` | `gen-ai-user` | QuickSight username for data source ownership |
| `image_bucket_exists` | `"true"` | Set by `deploy.sh`; controls import vs create for the image bucket |
