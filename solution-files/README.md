# Cloudage Image Rekognition

A production-ready, serverless image processing pipeline using AWS CDK, Python, and Amazon Rekognition.

## 🎯 Overview

This system automatically classifies images, stores results in DynamoDB, forwards data to downstream systems, and provides analytics through Amazon QuickSight.

**Key Services:**
- Amazon Rekognition - AI image classification
- AWS Lambda - Serverless compute
- Amazon DynamoDB - NoSQL database
- Amazon S3 - Storage
- Amazon SQS & SNS - Messaging
- Amazon Athena & QuickSight - Analytics

## 🏗️ Architecture

![Cloudage Architecture Diagram](https://raw.githubusercontent.com/VinayShinde-Cloud/AWS_Rekognition/main/Concepts/Recognition.drawio.png)

**Architecture Flow:**

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐                                            │
│  │   API Stack      │                                            │
│  │ • API Gateway    │                                            │
│  │ • Lambda (30s)   │                                            │
│  │ • S3 Bucket      │                                            │
│  │ • SNS/SQS        │                                            │
│  └────────┬─────────┘                                            │
│           │                                                      │
│  ┌────────▼──────────────────┐                                  │
│  │ Rekognition Stack         │                                  │
│  │ • Rekognition API         │                                  │
│  │ • Lambda (300s)           │                                  │
│  │ • DynamoDB                │                                  │
│  │ • SQS/SNS                 │                                  │
│  └────────┬──────────────────┘                                  │
│           │                                                      │
│  ┌────────▼──────────────────┐                                  │
│  │ Integration Stack         │                                  │
│  │ • XML Conversion          │                                  │
│  │ • Lambda (300s)           │                                  │
│  │ • HTTP Forwarding         │                                  │
│  │ • S3 XML Storage          │                                  │
│  └────────┬──────────────────┘                                  │
│           │                                                      │
│  ┌────────▼──────────────────┐                                  │
│  │ Visualization Stack       │                                  │
│  │ • Athena                  │                                  │
│  │ • Glue Crawler            │                                  │
│  │ • QuickSight              │                                  │
│  └───────────────────────────┘                                  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## ✨ Features

✅ Serverless & Scalable  
✅ Event-Driven (SQS/SNS)  
✅ Dead-Letter Queues & Alarms  
✅ Complete IAM Policies  
✅ QuickSight Analytics  

## 📁 Project Structure

```
AWS_ReKognition_AI_IDE_AWS_KIRO/
├── Concepts/                                    # Architecture & Design
│   ├── Recognition.drawio.png                  # Main architecture diagram
│   ├── ML_OpsAWSRekognition-with-Kiro.png     # ML Ops workflow
│   ├── VibeCoding.png                          # Development methodology
│   ├── SDLC-AiSDLC-AiDLC-CCSSD.png            # Development lifecycle
│   ├── TraditionalSoftwareDevelopmentCycle.png # SDLC overview
│   └── CoreDevVsDevOps.png                     # Dev vs DevOps
│
├── Examples/                                    # Sample Data & Reports
│   ├── athena.csv                              # Sample Athena results
│   ├── Speed_&_Lane_Analysis_*.pdf            # Traffic analysis reports
│   └── Traffic_Overview_*.pdf                 # Traffic visualization
│
├── Policies/                                    # AWS IAM Policies
│   ├── qs_users.json                          # QuickSight user policy
│   ├── s3_notification.json                   # S3 notification policy
│   ├── s3_result.json                         # S3 result bucket policy
│   ├── s3_verify.json                         # S3 verify bucket policy
│   ├── sns_attrs.json                         # SNS attributes policy
│   └── sns_policy.json                        # SNS publication policy
│
├── QuickSightFixes/                           # QuickSight Setup Guides
│   ├── QUICKSIGHT_IMPORT_GUIDE.md
│   ├── QUICKSIGHT_PERMISSION_FIX.md
│   ├── QUICKSIGHT_SETUP.md
│   ├── QUICKSIGHT_ROLES_ACCESS.md
│   └── QUICKSIGHT_READY.md
│
├── solution-files/
│   ├── README.md                               # 📖 Documentation
│   ├── cdk-outputs-*.json                      # Stack outputs (auto-generated)
│   ├── DEPLOYMENT_COMPLETE.md
│   ├── DEPLOYMENT_SETUP_COMPLETE.md
│   │
│   └── python/                                 # Python CDK Implementation
│       ├── app.py                              # CDK app entry point
│       ├── cdk.json                            # CDK context configuration
│       ├── deploy.sh                           # Bash deployment script
│       ├── deploy-simple.ps1                  # PowerShell deployment script
│       ├── requirements.txt                    # Python dependencies
│       ├── requirements-dev.txt                # Dev dependencies
│       ├── scan_classifications.py             # DynamoDB scan/seed utility
│       ├── send_images.py                      # Image upload utility
│       ├── cdk-outputs-APIStack.json          # APIStack outputs
│       ├── cdk-outputs-IntegrationStack.json  # IntegrationStack outputs
│       ├── cdk-outputs-RekognitionStack.json  # RekognitionStack outputs
│       ├── cdk-outputs-VisualizationStack.json # VisualizationStack outputs
│       │
│       ├── api/                                # APIStack - Image Ingestion
│       │   ├── __init__.py
│       │   ├── infrastructure.py               # Stack CDK definition
│       │   └── runtime/
│       │       ├── get_save_image.py           # Lambda: Download & upload
│       │       ├── get_save_image_solution.py  # Reference implementation
│       │       └── __pycache__/
│       │
│       ├── recognition/                        # RekognitionStack - Classification
│       │   ├── __init__.py
│       │   ├── infrastructure.py               # Stack CDK definition
│       │   └── runtime/
│       │       ├── image_recognition.py        # Lambda: Rekognition API call
│       │       ├── image_recognition_solution.py
│       │       ├── list_images.py              # Lambda: List classifications
│       │       ├── list_images_solution.py
│       │       └── __pycache__/
│       │
│       ├── integration/                        # IntegrationStack - Forwarding
│       │   ├── __init__.py
│       │   ├── infrastructure.py               # Stack CDK definition
│       │   └── runtime/
│       │       ├── send_email.py               # Lambda: XML conversion
│       │       ├── send_email_solution.py
│       │       ├── SaveXMLLambda.py            # Lambda: Save XML payload
│       │       ├── SaveXMLLambda_solution.py
│       │       └── __pycache__/
│       │
│       ├── visualization/                      # VisualizationStack - Analytics
│       │   ├── __init__.py
│       │   ├── infrastructure.py               # Stack CDK definition (no runtime)
│       │   └── __pycache__/
│       │
│       ├── iam/                                # IAM Policies & Roles
│       │   ├── deployer-user-policy.json      # Aggregate deployer policy
│       │   ├── deployer-policy-1-infra.json   # Infrastructure permissions
│       │   ├── deployer-policy-2-compute.json # Compute permissions
│       │   ├── deployer-policy-3-analytics.json # Analytics permissions
│       │   ├── fix-cdk-bootstrap-trust.sh     # Bootstrap trust fixer
│       │   ├── lambda-image-get-save-role.json
│       │   ├── lambda-image-recognition-role.json
│       │   ├── lambda-integration-role.json
│       │   ├── lambda-list-images-role.json
│       │   ├── lambda-save-xml-role.json
│       │   ├── lambda-athena-connector-role.json
│       │   └── glue-crawler-role.json
│       │
│       ├── cdk.out/                            # CDK synthesized templates
│       │   └── .cache/
│       │
│       └── .venv/                              # Python virtual environment
│           ├── bin/                            # Linux/Mac executables
│           ├── Scripts/                        # Windows executables
│           └── lib/                            # Site packages
│
├── .kiro/                                      # Kiro IDE Configuration
│   └── steering/                               # AI Development Guidance
│       ├── tech.md                             # Tech stack details
│       ├── structure.md                        # Project organization
│       └── product.md                          # Product overview
│
├── .git/                                       # Git repository
│
├── .gitignore                                  # Git ignore rules
├── CLEANUP_AND_TEARDOWN_GUIDE.md              # Cleanup instructions
├── DEPLOYMENT_COMPLETE.md
├── DEPLOYMENT_SETUP_COMPLETE.md
├── MANUAL_DEPLOYMENT_GUIDE.md                 # Manual deployment steps
└── ReadersAreTheLeaders.rtf                   # Project guidelines
```

### Key Directories Explained

| Directory | Purpose | Contains |
|-----------|---------|----------|
| `api/` | Image ingestion stack | API Gateway config, Lambda downloader |
| `recognition/` | AI classification stack | Rekognition Lambda, DynamoDB config |
| `integration/` | Data forwarding stack | XML converter, HTTP forwarder |
| `visualization/` | Analytics stack | Athena, Glue, QuickSight config |
| `iam/` | Security policies | IAM roles and permissions |
| `Concepts/` | Architecture diagrams | Visual documentation |
| `Examples/` | Sample data | Test data and report examples |
| `Policies/` | AWS policies | IAM policy documents |
| `QuickSightFixes/` | Setup guides | QuickSight configuration guides |
| `.kiro/` | Kiro IDE config | Development guidance and rules |

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js & AWS CDK
- AWS CLI v2 configured
- AWS Account with QuickSight

### Installation & Deployment

```bash
# Clone repository
git clone https://github.com/VinayShinde-Cloud/AWS_Rekognition.git
cd AWS_Rekognition/solution-files/python

# Setup
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Deploy
./deploy.sh --region us-east-1  # Bash
# OR
.\deploy-simple.ps1             # PowerShell
```

### Testing

```bash
# Get API endpoint
cat cdk-outputs-APIStack.json

# Upload image
curl "https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/?url=https://example.com/image.jpg&name=test.jpg"

# List images
curl "https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/"

# Seed test data
python scan_classifications.py --seed --region us-east-1
```

## 🏗️ 4 Stacks

| Stack | Purpose |
|-------|---------|
| **APIStack** | REST API, S3 image bucket, SQS/SNS |
| **RekognitionStack** | Rekognition API, DynamoDB storage |
| **IntegrationStack** | XML conversion, downstream forwarding |
| **VisualizationStack** | Athena, Glue, QuickSight |

## 🔧 AWS Account Config

```
Account ID: 784055307907
IAM User: Vinay-AI
Region: us-east-1
Asset Bucket: rekognition-915916
QuickSight User: Vinay-AI
```

Update `cdk.json` for different account:
```json
{
  "context": {
    "asset_bucket": "your-bucket",
    "image_bucket_prefix": "your-prefix",
    "quicksight_user": "your-user"
  }
}
```

## 📊 Deployment Commands

```bash
# Deploy all stacks
./deploy.sh --region us-east-1

# Deploy single stack
./deploy.sh --stack APIStack

# Preview changes
./deploy.sh --diff

# Destroy stacks
./deploy.sh --destroy

# Cleanup orphaned resources
./deploy.sh --cleanup
```

## 🔒 Security

✅ Least-privilege IAM roles  
✅ S3 encryption & SSL enforcement  
✅ DLQs for error tracking  
✅ CloudWatch monitoring  
✅ No hardcoded credentials  

## � Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11 |
| IaC | AWS CDK v2 |
| AI | Amazon Rekognition |
| Compute | AWS Lambda |
| Storage | S3, DynamoDB |
| Messaging | SNS, SQS |
| Analytics | Athena, Glue, QuickSight |

## 🤝 Contributing

Areas for improvement:
- Unit tests for Lambda functions
- CI/CD pipeline (GitHub Actions)
- Additional Rekognition features
- Multi-region deployment

## 📄 License

Free to use for learning, experimentation, and building amazing things.

  
Repository: [github.com/VinayShinde-Cloud/AWS_Rekognition](https://github.com/VinayShinde-Cloud/AWS_Rekognition)

---

**Python:** 3.11 | **CDK:** 2.118.0 | **Status:** Production-Ready
