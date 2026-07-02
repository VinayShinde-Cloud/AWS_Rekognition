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
solution-files/python/
├── app.py                  # CDK entry point
├── cdk.json               # Configuration
├── deploy.sh              # Bash deployment
├── deploy-simple.ps1      # PowerShell deployment
├── requirements.txt       # Dependencies
├── api/                   # Image ingestion
├── recognition/           # AI classification
├── integration/           # XML forwarding
├── visualization/         # Analytics
└── iam/                   # IAM policies
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

## 👤 Author

**Ajit Jadhav**  
Repository: [github.com/VinayShinde-Cloud/AWS_Rekognition](https://github.com/VinayShinde-Cloud/AWS_Rekognition)

---

**Python:** 3.11 | **CDK:** 2.118.0 | **Status:** Production-Ready
