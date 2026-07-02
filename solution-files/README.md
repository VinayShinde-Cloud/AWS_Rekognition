# Cloudage Image Rekognition

Production-ready serverless image processing pipeline using AWS CDK, Python, and Amazon Rekognition.

## Overview

Automatically classify images, store results in DynamoDB, forward to downstream systems, and visualize in QuickSight.

**Key Services:** Rekognition • Lambda • DynamoDB • S3 • SQS/SNS • Athena • QuickSight

## Architecture

```
Upload → APIStack → Rekognition → DynamoDB
  ↓         ↓           ↓
 S3      SNS/SQS    Integration → XML → QuickSight
```

## Quick Start

```bash
# Setup
git clone https://github.com/VinayShinde-Cloud/AWS_Rekognition.git
cd AWS_Rekognition/solution-files/python
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Deploy
./deploy.sh --region us-east-1  # Bash
# OR
.\deploy-simple.ps1             # PowerShell

# Test
curl "https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/?url=https://example.com/image.jpg&name=test.jpg"
```

## Project Structure

```
AWS_ReKognition_AI_IDE_AWS_KIRO/
├── Concepts/              # Architecture diagrams
├── Examples/              # Sample data
├── Policies/              # IAM policies
├── QuickSightFixes/       # Setup guides
└── solution-files/
    └── python/
        ├── api/           # Image ingestion (APIStack)
        ├── recognition/   # AI classification (RekognitionStack)
        ├── integration/   # XML forwarding (IntegrationStack)
        ├── visualization/ # Analytics (VisualizationStack)
        ├── iam/           # IAM policies
        ├── app.py         # CDK entry point
        ├── deploy.sh      # Bash deployment
        └── deploy-simple.ps1  # PowerShell deployment
```

## 4 Stacks

| Stack | Purpose |
|-------|---------|
| **APIStack** | REST API, S3, SQS/SNS |
| **RekognitionStack** | Rekognition, DynamoDB |
| **IntegrationStack** | XML conversion, forwarding |
| **VisualizationStack** | Athena, Glue, QuickSight |

## AWS Account

```
Account ID: 784055307907
IAM User: Vinay-AI
Region: us-east-1
Asset Bucket: rekognition-915916
```

## Features

✅ Serverless & Scalable  
✅ Event-Driven (SQS/SNS)  
✅ Dead-Letter Queues  
✅ Complete IAM Policies  
✅ QuickSight Analytics  

## Deployment

```bash
./deploy.sh --region us-east-1          # Deploy all
./deploy.sh --stack APIStack            # Deploy single stack
./deploy.sh --diff                      # Preview changes
./deploy.sh --destroy                   # Destroy stacks
./deploy.sh --cleanup                   # Cleanup orphaned resources
```

## Tech Stack

- **Language:** Python 3.11
- **IaC:** AWS CDK v2
- **AI:** Amazon Rekognition
- **Database:** DynamoDB
- **Storage:** S3
- **Messaging:** SNS, SQS
- **Analytics:** Athena, Glue, QuickSight

## License

Free to use for learning and experimentation.

## Author
 
Repository: [github.com/VinayShinde-Cloud/AWS_Rekognition](https://github.com/VinayShinde-Cloud/AWS_Rekognition)

---

**Python:** 3.11 | **CDK:** 2.118.0 | **Status:** Production-Ready
