# Project Structure

## Repository Layout

```
AWS_ReKognition_AI_IDE_AWS_KIRO/
├── Concepts/                              # Architecture diagrams and concept visuals
│   ├── AI-DevelopmentLifeCycle-Spectrum.png
│   ├── ML_OpsAWSRekognition-with-Kiro.png
│   ├── Recognition.drawio.png
│   ├── TraditionalSoftwareDevelopmentCycle.png
│   └── ...
├── Examples/                              # Example data and output reports
│   ├── athena.csv                        # Sample Athena query results
│   ├── Speed_&_Lane_Analysis_*.pdf       # Report examples
│   └── Traffic_Overview_*.pdf
├── solution-files/                        # Main project (all implementation here)
│   ├── README.md                          # Comprehensive project documentation
│   └── python/                            # Python implementation
├── ReadersAreTheLeaders.rtf               # Project setup guidelines
└── .kiro/                                 # Kiro IDE configuration
    └── steering/                          # AI assistance guidance (THIS DIRECTORY)
        ├── product.md                     # Product overview
        ├── tech.md                        # Tech stack, build commands, patterns
        └── structure.md                   # This file — project organization
```

## Python Project Structure

The entire implementation lives in `solution-files/python/`.

### Root-Level Files

```
solution-files/python/
├── app.py                                 # CDK app entry point
│                                          # • Imports all 4 stack classes
│                                          # • Instantiates them in sequence
│                                          # • Reads AWS account/region from environment
│                                          # • No hardcoded values
│
├── cdk.json                               # CDK context configuration
│                                          # • asset_bucket: S3 bucket for layer zip
│                                          # • image_bucket_prefix: image bucket naming
│                                          # • layer_zip_key: S3 key for requests layer
│                                          # • quicksight_user: QuickSight data source owner
│                                          # • image_bucket_exists: auto-set by deploy.sh
│
├── requirements.txt                       # Python dependencies
│                                          # Core: aws-cdk-lib, constructs, boto3, botocore
│
├── requirements-dev.txt                   # Development dependencies (if any)
│
├── deploy.sh                              # Main deployment orchestration script
│                                          # CRITICAL FILE — handles:
│                                          # • Validation (AWS CLI, CDK, Python venv)
│                                          # • CDK bootstrap
│                                          # • Asset bucket creation + layer zip upload
│                                          # • Image bucket existence detection
│                                          # • Orphaned resource cleanup
│                                          # • Stack deployment in order
│                                          # • Glue crawler startup
│                                          # • QuickSight service role permissions
│                                          # • Supports: --stack, --diff, --destroy, --cleanup
│
├── scan_classifications.py                # DynamoDB utility script
│                                          # Usage: python scan_classifications.py [--seed] [--region]
│                                          # • --seed: populate test classifications
│                                          # • --region: specify AWS region
│
├── send_images.py                         # Image submission utility (optional)
│
├── requests_layer3_11.zip                 # Pre-built Lambda layer
│                                          # • Contains requests library for Python 3.11
│                                          # • Uploaded to asset bucket by deploy.sh
│
└── cdk-outputs-*.json                     # Stack output files (auto-generated)
    ├── cdk-outputs-APIStack.json
    ├── cdk-outputs-IntegrationStack.json
    ├── cdk-outputs-RekognitionStack.json
    └── cdk-outputs-VisualizationStack.json
```

### Stack Modules (4 stacks)

Each stack follows the same structure: `infrastructure.py` (CDK definition) + `runtime/` (Lambda handlers).

#### 1. APIStack — Image Ingestion

```
api/
├── __init__.py
├── infrastructure.py                      # CDK stack definition (AIStack class)
│                                          # • Creates API Gateway with GET endpoint
│                                          # • Lambda function: ImageGetAndSaveLambda
│                                          # • S3 bucket: image storage (RemovalPolicy.RETAIN)
│                                          # • SNS topic: image_uploaded (published when S3 event fires)
│                                          # • SQS queue: upload_queue (EventSource for Rekognition)
│                                          # • SQS DLQ: upload_dlq (with CloudWatch alarm)
│                                          # • IAM role with S3 PutObject permission
│                                          # • Lambda layer: requests library
│                                          # • API Gateway throttling: 100 rps / 200 burst
│                                          # • Lambda timeout: 30s
│
└── runtime/
    ├── get_save_image.py                  # TODO: Lambda handler (workshop module)
    │                                      # • Download image from URL (function: get_file_from_url)
    │                                      # • Upload to S3 (function: upload_to_s3)
    │                                      # • Handle HTTP errors gracefully
    │                                      # • Return statusCode 200/400/502 with body
    │
    └── get_save_image_solution.py         # Reference implementation (read-only)
```

#### 2. IntegrationStack — Downstream Forwarding

```
integration/
├── __init__.py
├── infrastructure.py                      # CDK stack definition (IntegrationStack class)
│                                          # • SNS topic: image_recognized
│                                          # • SQS queue: rekognized_queue (EventSource for send_email)
│                                          # • SQS DLQ: rekognized_dlq (with alarm)
│                                          # • Lambda: send_email (polls rekognized_queue)
│                                          # • Lambda: SaveXMLLambda (receives XML POST)
│                                          # • API Gateway: /save endpoint for SaveXMLLambda
│                                          # • S3 bucket: XML output storage
│                                          # • SSM Parameter: endpoint_url (downstream HTTP target)
│                                          # • IAM roles with least-privilege permissions
│                                          # • SQS visibility timeout: 1800s (6× 300s Lambda timeout)
│
└── runtime/
    ├── send_email.py                      # TODO: Lambda handler (workshop module)
    │                                      # • Poll SQS rekognized_queue (via event source mapping)
    │                                      # • Convert Rekognition results to XML
    │                                      # • HTTP POST XML to downstream endpoint (URL from SSM)
    │                                      # • Handle HTTP errors gracefully
    │
    ├── send_email_solution.py             # Reference implementation
    │
    ├── SaveXMLLambda.py                   # TODO: Lambda handler (workshop module)
    │                                      # • Receive XML payload via API Gateway POST
    │                                      # • Validate XML structure
    │                                      # • Write to S3 with timestamped key
    │                                      # • Return statusCode 200/400/500
    │
    └── SaveXMLLambda_solution.py          # Reference implementation (note: *_solution naming)
```

#### 3. RekognitionStack — Classification & Storage

```
recognition/
├── __init__.py
├── infrastructure.py                      # CDK stack definition (RekognitionStack class)
│                                          # • DynamoDB table: Classifications
│                                          #   - Partition key: image (String)
│                                          #   - On-demand billing (auto-scaling)
│                                          #   - RemovalPolicy.RETAIN (survives destroy)
│                                          # • Lambda: image_recognition
│                                          #   - Event source: upload_queue (from APIStack)
│                                          #   - Timeout: 300s (5 minutes)
│                                          #   - Subscribes to SNS image_recognized topic
│                                          # • Lambda: list_images
│                                          #   - API Gateway GET / endpoint
│                                          #   - Returns all items from Classifications table
│                                          # • API Gateway: /images endpoint for list_images
│                                          # • IAM roles with Rekognition + DynamoDB permissions
│
└── runtime/
    ├── image_recognition.py               # TODO: Lambda handler (workshop module)
    │                                      # • Receive S3 object key from SQS event
    │                                      # • Call Rekognition.detect_labels (max 10, 70% confidence)
    │                                      # • Write results to DynamoDB (image, labels, confidence, etc.)
    │                                      # • Publish to SNS image_recognized topic
    │                                      # • Handle Rekognition errors (throttling, invalid image, etc.)
    │
    ├── image_recognition_solution.py      # Reference implementation
    │
    ├── list_images.py                     # TODO: Lambda handler (workshop module)
    │                                      # • Scan DynamoDB Classifications table
    │                                      # • Return JSON array of all classifications
    │                                      # • Handle pagination if large result sets
    │
    └── list_images_solution.py            # Reference implementation
```

#### 4. VisualizationStack — Analytics & Dashboards

```
visualization/
├── __init__.py
└── infrastructure.py                      # CDK stack definition (VisualizationStack class)
                                           # NO RUNTIME CODE — infrastructure only
                                           # • Athena DynamoDB connector (SAR)
                                           # • Lambda: AthenaConnectorLambda (handles federated queries)
                                           # • Glue crawler: dynamodb-classifications-crawler
                                           # • Glue database: recognitiondb
                                           # • Athena workgroup: dynamodb-visualization
                                           # • Athena data catalog
                                           # • QuickSight data source
                                           # • IAM role: ConnectorLambdaRole
                                           #   - AWSLambdaBasicExecutionRole
                                           #   - AmazonDynamoDBFullAccess
                                           #   - AmazonS3FullAccess
                                           #   - AWSQuicksightAthenaAccess
```

### IAM Policies

```
iam/
├── deployer-user-policy.json              # Aggregate of all 3 policies below
│                                          # • Attach to IAM user running ./deploy.sh
│
├── deployer-policy-1-infra.json           # Infrastructure permissions
│                                          # • S3, CloudFormation, CDK bootstrap
│
├── deployer-policy-2-compute.json         # Compute & messaging permissions
│                                          # • Lambda, API Gateway, SQS, SNS, DynamoDB, IAM
│
├── deployer-policy-3-analytics.json       # Analytics permissions
│                                          # • Athena, Glue, QuickSight, Rekognition, SSM
│
├── fix-cdk-bootstrap-trust.sh             # Shell script
│                                          # • Fixes CDK bootstrap role trust policies
│                                          # • Run once after cdk bootstrap
│                                          # • deploy.sh calls this automatically
│
└── lambda-*-role.json (7 files)           # Reference IAM role definitions
    ├── lambda-image-get-save-role.json
    ├── lambda-image-recognition-role.json
    ├── lambda-integration-role.json
    ├── lambda-list-images-role.json
    ├── lambda-save-xml-role.json
    ├── lambda-athena-connector-role.json
    └── glue-crawler-role.json
```

### Virtual Environment

```
.venv/                                    # Python virtual environment (gitignored)
├── bin/                                  # Executables (Linux/Mac)
├── Scripts/                              # Executables (Windows)
├── lib/                                  # Site-packages with dependencies
└── pyvenv.cfg                            # Environment config
```

## Data Flow Across Stacks

```
┌─────────────────────────────────────────────────────────────────┐
│ Client Request (APIStack)                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
         GET /?url=<image_url>&name=<filename>
                              ↓
    ┌───────────────────────────────────────────┐
    │ API Gateway (APIStack)                    │
    │  └─ ImageGetAndSaveLambda                │
    │     • Download image from URL            │
    │     • Put object to S3 (image_bucket)   │
    └───────────────────────────────────────────┘
                              ↓
    ┌───────────────────────────────────────────┐
    │ S3 Event Notification (APIStack)          │
    │  └─ S3 ObjectCreated:Put event            │
    │     └─ SNS Topic: image_uploaded          │
    │        └─ SQS Queue: upload_queue         │
    └───────────────────────────────────────────┘
                              ↓
    ┌───────────────────────────────────────────┐
    │ Lambda Event Source Mapping               │
    │  └─ image_recognition Lambda triggered   │
    │     (RekognitionStack)                   │
    │     • Poll upload_queue                  │
    │     • Call Rekognition.detect_labels     │
    │     • Write results to DynamoDB          │
    │     • Publish to SNS image_recognized    │
    └───────────────────────────────────────────┘
                              ↓
    ┌───────────────────────────────────────────┐
    │ SNS to SQS (IntegrationStack)            │
    │  └─ SNS: image_recognized topic          │
    │     └─ SQS Queue: rekognized_queue       │
    └───────────────────────────────────────────┘
                              ↓
    ┌───────────────────────────────────────────┐
    │ Lambda Event Source Mapping               │
    │  └─ send_email Lambda triggered          │
    │     (IntegrationStack)                   │
    │     • Poll rekognized_queue              │
    │     • Convert to XML                     │
    │     • HTTP POST to downstream endpoint   │
    │       (URL from SSM Parameter Store)     │
    └───────────────────────────────────────────┘
                              ↓
    ┌───────────────────────────────────────────┐
    │ SaveXMLLambda (IntegrationStack)          │
    │  └─ Receive XML POST                      │
    │     • Validate XML                        │
    │     • Write to S3 (xml_bucket) with       │
    │       timestamped key                     │
    └───────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│ Analytics Pipeline (VisualizationStack)                         │
└─────────────────────────────────────────────────────────────────┘

    DynamoDB (Classifications table)
                      ↓
    Athena DynamoDB Connector (SAR Lambda)
                      ↓
    Glue Crawler (schema discovery)
                      ↓
    Athena Workgroup (SQL queries)
                      ↓
    QuickSight (dashboards & visualizations)
```

## File Naming Conventions

| Item | Pattern | Example |
|------|---------|---------|
| Stack class | `<Domain>Stack` | `APIStack`, `RekognitionStack` |
| Lambda function (CDK) | `<Action>Lambda` or lowercase | `ImageGetAndSaveLambda`, `image_recognition` |
| Lambda handler file | `<action>.py` | `get_save_image.py`, `image_recognition.py` |
| Solution file | `<handler>_solution.py` | `get_save_image_solution.py` |
| DynamoDB table | Plural noun | `Classifications` (not `Classification`) |
| SQS queue | `<domain>_queue` or `<action>_queue` | `upload_queue`, `rekognized_queue` |
| SQS DLQ | `<queue_name>_dlq` | `upload_dlq`, `rekognized_dlq` |
| S3 bucket | `<purpose>-<region>-<account>` | `sagemaker-us-east-1-123456789012` |
| SNS topic | `<event>_topic` | `image_uploaded_topic`, `image_recognized_topic` |
| IAM role | `<service>-<resource>-role` | `lambda-image-recognition-role`, `glue-crawler-role` |
| CDK construct | PascalCase (AWS standard) | `Bucket`, `Function`, `Queue` |

## Key Directories & Their Purpose

| Directory | Purpose | Can Modify? |
|-----------|---------|------------|
| `api/runtime/` | Image ingestion Lambda handlers | ✓ Implement TODO functions |
| `recognition/runtime/` | Classification Lambda handlers | ✓ Implement TODO functions |
| `integration/runtime/` | Integration Lambda handlers | ✓ Implement TODO functions |
| `*/infrastructure.py` | Stack CDK definitions | ✓ Core implementation area |
| `*_solution.py` | Reference implementations | ✗ Read-only (for learning) |
| `iam/` | IAM policies and roles | ✓ Update if permissions needed |
| `.venv/` | Python virtual environment | ✗ Don't commit, regenerate locally |

## Output Artifacts

After running `./deploy.sh`, these files are created:

- **cdk-outputs-APIStack.json** — API Gateway endpoint, SNS topic ARN, SQS queue URLs
- **cdk-outputs-IntegrationStack.json** — SNS/SQS ARNs, SSM parameter name, SaveXMLLambda endpoint
- **cdk-outputs-RekognitionStack.json** — DynamoDB table name, Lambda function ARNs
- **cdk-outputs-VisualizationStack.json** — Athena workgroup, QuickSight dataset ARN

These files are used for:
- Stack-to-stack dependencies at synth time
- Manual testing and debugging
- QuickSight configuration

## Key Design Constraints

1. **Stack isolation** — Each stack is independent but may depend on outputs from prior stacks (read via JSON files, not CloudFormation exports)
2. **Configuration centralization** — All runtime config in `cdk.json` context or environment variables
3. **No cross-account** — All stacks deploy to same AWS account and region
4. **Lambda layer reuse** — Requests library layer shared across all Lambdas to save cold start time
5. **Event-driven async** — Pipeline uses SNS/SQS messaging, not direct Lambda invocation
6. **Resilience patterns** — All queues have DLQs; all DLQs have CloudWatch alarms

## Typical Workflow

```
1. cd solution-files/python
2. python3 -m venv .venv
3. source .venv/bin/activate
4. pip install -r requirements.txt
5. aws configure  # Set AWS credentials
6. ./deploy.sh    # Deploy all stacks (10-15 minutes)
7. python scan_classifications.py --seed  # Load test data
8. curl "https://<api-id>.../prod/?url=<image-url>&name=photo.jpg"  # Test upload
9. Check CloudWatch logs for execution flow
10. Log into QuickSight to view dashboards
```
