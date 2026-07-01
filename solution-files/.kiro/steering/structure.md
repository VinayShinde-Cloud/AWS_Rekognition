# Project Structure

All source lives under `python/`. Run all commands from that directory.

```
python/
├── app.py                          # CDK app entry point — instantiates all 4 stacks
├── cdk.json                        # CDK context config (bucket names, prefixes, flags)
├── deploy.sh                       # Main deploy/destroy/diff script
├── requirements.txt                # Runtime deps (aws-cdk-lib, constructs, boto3)
├── requirements-dev.txt            # Dev deps
├── scan_classifications.py         # CLI utility to scan/seed the DynamoDB table
├── requests_layer3_11.zip          # Pre-built Lambda layer (requests lib)
│
├── api/                            # APIStack — image upload entry point
│   ├── infrastructure.py           # CDK stack: API Gateway → Lambda → S3 → SNS → SQS
│   └── runtime/
│       ├── get_save_image.py       # Lambda: downloads image from URL, saves to S3
│       └── get_save_image_solution.py
│
├── recognition/                    # RekognitionStack — image classification
│   ├── infrastructure.py           # CDK stack: SQS → Lambda → Rekognition → DynamoDB → SNS
│   └── runtime/
│       ├── image_recognition.py    # Lambda: runs Rekognition, writes to DynamoDB, triggers SNS
│       ├── image_recognition_solution.py
│       ├── list_images.py          # Lambda: scans DynamoDB, returns all classified images
│       └── list_images_solution.py
│
├── integration/                    # IntegrationStack — downstream XML forwarding
│   ├── infrastructure.py           # CDK stack: SNS → SQS → Lambda → SSM → API Gateway
│   └── runtime/
│       ├── send_email.py           # Lambda: converts rekognition results to XML, POSTs to endpoint
│       ├── send_email_solution.py
│       └── SaveXMLLambda.py        # Lambda: receives XML POST, saves to S3
│
├── visualization/                  # VisualizationStack — QuickSight analytics
│   └── infrastructure.py           # CDK stack: DynamoDB → Athena connector → Glue → QuickSight
│
├── iam/                            # IAM policy documents and helper scripts
│   ├── README.md
│   ├── deployer-user-policy.json   # Minimum permissions for the deploy IAM user
│   ├── fix-cdk-bootstrap-trust.sh  # Patches CDK bootstrap role trust policies
│   └── *.json                      # Per-Lambda IAM role definitions (reference)
│
└── cdk-outputs-*.json              # Stack outputs written by deploy.sh (gitignored)
```

## Architecture & Data Flow

```
User → API Gateway (APIStack)
         → ImageGetAndSaveLambda → S3 (image bucket)
                                     → SNS → SQS (upload queue)
                                               → image_recognition Lambda (RekognitionStack)
                                                   → Rekognition DetectLabels
                                                   → DynamoDB (Classifications table)
                                                   → SNS → SQS (rekognized queue)
                                                               → IntegrationLambda (IntegrationStack)
                                                                   → SSM (endpoint URL)
                                                                   → SaveXMLLambda via API Gateway

DynamoDB → Athena federated query (VisualizationStack)
             → Glue Data Catalog → QuickSight
```

## Key Conventions

- **One stack per domain folder** — `api/`, `recognition/`, `integration/`, `visualization/`
- **Infrastructure separate from runtime** — `infrastructure.py` (CDK) lives alongside a `runtime/` subfolder (Lambda code)
- **Solution files** — every Lambda has a `*_solution.py` counterpart with the reference implementation; never modify solution files
- **IAM** — all Lambda roles are explicitly defined with least-privilege inline policies; avoid `*` on resources except where AWS requires it (Rekognition, Glue catalog)
- **SQS visibility timeout** — must be ≥ 6× the Lambda timeout to prevent duplicate processing
- **DLQs** — every SQS queue has a dead-letter queue with a CloudWatch alarm on `ApproximateNumberOfMessagesVisible`
- **S3 buckets** — all buckets use `BLOCK_ALL` public access, S3-managed encryption, SSL enforcement, and `RETAIN` removal policy (except Athena spill/results which use `DESTROY`)
- **CDK context** — runtime config (bucket names, prefixes) flows through `cdk.json` context keys, never hardcoded; override with `-c key=value`
- **Stack outputs** — cross-stack values are passed as constructor parameters (plain strings), not CDK tokens, to avoid CloudFormation export locks
- **boto3 clients** — instantiated at module level (outside the handler) for Lambda connection reuse
- **Logging** — use `logging` module with `logger = logging.getLogger()` / `logger.setLevel(logging.INFO)`; never use bare `print()` in Lambda handlers
