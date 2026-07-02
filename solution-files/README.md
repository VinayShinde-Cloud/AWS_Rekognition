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
AWS-Rekognition/
└── AWS_ReKognition_AI_IDE_AWS_KIRO/
    ├── Concepts/                              # Architecture diagrams and concepts
    │   ├── Recognition.drawio.png             # Main architecture diagram
    │   ├── VibeCoding.png                     # Development methodology
    │   ├── ML_OpsAWSRekognition-with-Kiro.png
    │   └── ...
    │
    ├── Examples/                              # Sample data and reports
    │   ├── athena.csv
    │   └── Traffic_Overview_*.pdf
    │
    ├── Policies/                              # AWS IAM Policies
    │   ├── qs_users.json
    │   ├── s3_notification.json
    │   └── ...
    │
    ├── QuickSightFixes/                       # QuickSight setup guides
    │   ├── QUICKSIGHT_SETUP.md
    │   └── ...
    │
    ├── solution-files/
    │   ├── README.md                          # 📖 Documentation (START HERE)
    │   │
    │   └── python/                            # Python CDK Implementation
    │       ├── app.py                         # CDK app entry point
    │       ├── cdk.json                       # Configuration
    │       ├── deploy.sh                      # 🚀 Bash deployment
    │       ├── deploy-simple.ps1              # 🚀 PowerShell deployment
    │       ├── requirements.txt               # Python dependencies
    │       ├── scan_classifications.py        # DynamoDB utility
    │       ├── send_images.py                 # Image upload utility
    │       │
    │       ├── api/                           # APIStack - Image ingestion
    │       │   ├── infrastructure.py
    │       │   └── runtime/
    │       │       ├── get_save_image.py
    │       │       └── get_save_image_solution.py
    │       │
    │       ├── recognition/                   # RekognitionStack - AI classification
    │       │   ├── infrastructure.py
    │       │   └── runtime/
    │       │       ├── image_recognition.py
    │       │       ├── image_recognition_solution.py
    │       │       ├── list_images.py
    │       │       └── list_images_solution.py
    │       │
    │       ├── integration/                   # IntegrationStack - Data forwarding
    │       │   ├── infrastructure.py
    │       │   └── runtime/
    │       │       ├── send_email.py
    │       │       ├── send_email_solution.py
    │       │       ├── SaveXMLLambda.py
    │       │       └── SaveXMLLambda_solution.py
    │       │
    │       ├── visualization/                 # VisualizationStack - Analytics
    │       │   └── infrastructure.py
    │       │
    │       └── iam/                           # IAM policies and roles
    │           ├── deployer-user-policy.json
    │           ├── deployer-policy-1-infra.json
    │           ├── deployer-policy-2-compute.json
    │           ├── deployer-policy-3-analytics.json
    │           └── fix-cdk-bootstrap-trust.sh
    │
    ├── .kiro/                                 # Kiro IDE Configuration
    │   └── steering/
    │       ├── tech.md                        # Tech stack details
    │       ├── structure.md                   # Project organization
    │       └── product.md                     # Product overview
    │
    ├── deploy-simple.ps1                      # Root-level PowerShell deployment
    ├── CLEANUP_AND_TEARDOWN_GUIDE.md
    ├── DEPLOYMENT_COMPLETE.md
    ├── DEPLOYMENT_SETUP_COMPLETE.md
    ├── MANUAL_DEPLOYMENT_GUIDE.md
    ├── ReadersAreTheLeaders.rtf
    └── .gitignore
```

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
