# Cloudage Image Rekognition

A production-ready, serverless image processing pipeline built with AWS CDK, Python, and Amazon Rekognition. This system automatically classifies images, stores results in DynamoDB, forwards data to downstream systems, and provides rich analytics through Amazon QuickSight.

## 🎯 Overview

This project demonstrates a complete AWS serverless architecture for image processing and classification using:

- **Amazon Rekognition** - AI-powered image label detection
- **AWS Lambda** - Serverless compute for all processing steps
- **Amazon DynamoDB** - NoSQL database for classification results
- **Amazon S3** - Scalable image and data storage
- **Amazon SQS & SNS** - Reliable message queuing and pub/sub
- **Amazon Athena & QuickSight** - Federated queries and visualization
- **AWS CDK** - Infrastructure as Code in Python

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│ CLIENT REQUEST                                      │
│ GET /?url=<image_url>&name=<filename>              │
└──────────────────┬──────────────────────────────────┘
                   │
          ┌────────▼────────────────┐
          │ APIStack                │
          │ • API Gateway           │
          │ • ImageGetSaveLambda    │
          │ • S3 Image Bucket       │
          │ • SNS/SQS Pipeline      │
          └────────┬────────────────┘
                   │
          ┌────────▼────────────────┐
          │ RekognitionStack        │
          │ • Rekognition API       │
          │ • DynamoDB              │
          │ • Lambda Processor      │
          └────────┬────────────────┘
                   │
          ┌────────▼────────────────┐
          │ IntegrationStack        │
          │ • XML Conversion        │
          │ • HTTP Forwarding       │
          │ • S3 XML Storage        │
          └────────┬────────────────┘
                   │
          ┌────────▼────────────────┐
          │ VisualizationStack      │
          │ • Athena Connector      │
          │ • Glue Crawler          │
          │ • QuickSight Dashboard  │
          └─────────────────────────┘
```

## ✨ Key Features

✅ **Serverless & Scalable** - Auto-scales from zero to millions of images  
✅ **Event-Driven** - Fully asynchronous processing with SQS/SNS  
✅ **Fault Tolerant** - Dead-letter queues and CloudWatch alarms  
✅ **Production Ready** - Complete IAM policies and security best practices  
✅ **Analytics Ready** - QuickSight dashboards via Athena federated queries  
✅ **Well Documented** - Comprehensive setup and troubleshooting guides  

## 📁 Project Structure

```
AWS-Rekognition/
├── Concepts/                                    # Architecture diagrams
│   ├── Recognition.drawio.png                  # Main architecture
│   ├── VibeCoding.png                          # Development flow
│   ├── ML_OpsAWSRekognition-with-Kiro.png     # ML Ops overview
│   └── SDLC-AiSDLC-AiDLC-CCSSD.png            # Development lifecycle
│
├── Examples/                                    # Sample data & reports
│   ├── athena.csv                              # Sample Athena results
│   ├── Speed_&_Lane_Analysis_*.pdf            # Traffic analysis reports
│   └── Traffic_Overview_*.pdf                 # Traffic overview reports
│
├── Policies/                                    # AWS IAM Policies
│   ├── qs_users.json                          # QuickSight user policy
│   ├── s3_notification.json                   # S3 notification policy
│   ├── s3_result.json                         # S3 result bucket policy
│   ├── s3_verify.json                         # S3 verify bucket policy
│   ├── sns_attrs.json                         # SNS attributes policy
│   └── sns_policy.json                        # SNS policy
│
├── QuickSightFixes/                           # QuickSight setup guides
│   ├── QUICKSIGHT_IMPORT_GUIDE.md
│   ├── QUICKSIGHT_PERMISSION_FIX.md
│   └── QUICKSIGHT_SETUP.md
│
├── solution-files/
│   ├── README.md                               # 📖 START HERE
│   └── python/                                 # Python CDK Implementation
│       ├── app.py                              # CDK entry point
│       ├── cdk.json                            # Configuration
│       ├── deploy.sh                           # 🚀 Bash deployment script
│       ├── deploy-simple.ps1                  # 🚀 PowerShell deployment script
│       ├── requirements.txt                    # Dependencies
│       ├── scan_classifications.py             # DynamoDB utility
│       ├── send_images.py                     # Image upload utility
│       │
│       ├── api/                                # APIStack
│       │   ├── infrastructure.py
│       │   └── runtime/
│       │       ├── get_save_image.py
│       │       └── get_save_image_solution.py
│       │
│       ├── recognition/                        # RekognitionStack
│       │   ├── infrastructure.py
│       │   └── runtime/
│       │       ├── image_recognition.py
│       │       ├── image_recognition_solution.py
│       │       ├── list_images.py
│       │       └── list_images_solution.py
│       │
│       ├── integration/                        # IntegrationStack
│       │   ├── infrastructure.py
│       │   └── runtime/
│       │       ├── send_email.py
│       │       ├── send_email_solution.py
│       │       ├── SaveXMLLambda.py
│       │       └── SaveXMLLambda_solution.py
│       │
│       ├── visualization/                      # VisualizationStack
│       │   └── infrastructure.py
│       │
│       └── iam/                                # IAM Policies
│           ├── deployer-user-policy.json
│           ├── deployer-policy-1-infra.json
│           ├── deployer-policy-2-compute.json
│           ├── deployer-policy-3-analytics.json
│           └── fix-cdk-bootstrap-trust.sh
│
└── .kiro/steering/                             # Development guidance
    ├── tech.md                                 # Tech stack details
    ├── structure.md                            # Project organization
    └── product.md                              # Product overview
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js** (for AWS CDK CLI)
- **AWS CLI v2** configured
- **AWS account** with QuickSight subscription

### Installation

```bash
# Clone the repository
git clone https://github.com/VinayShinde-Cloud/AWS_Rekognition.git
cd AWS_Rekognition/solution-files/python

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On Linux/Mac:
source .venv/bin/activate
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Deployment (Bash)

```bash
# Deploy all stacks
./deploy.sh --region us-east-1

# Deploy single stack
./deploy.sh --stack APIStack --region us-east-1
```

### Deployment (Windows PowerShell)

```powershell
# Deploy all stacks
.\deploy-simple.ps1

# Set AWS region (default: us-east-1)
$env:AWS_REGION = "us-east-1"
.\deploy-simple.ps1
```

### Testing

```bash
# Get API endpoint
cat cdk-outputs-APIStack.json

# Upload an image
curl "https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/?url=https://example.com/image.jpg&name=test.jpg"

# List classified images
curl "https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/"

# Seed test data
python scan_classifications.py --seed --region us-east-1
```

## 📚 Documentation

For detailed documentation, see:

- 👉 **[Complete Documentation](./README.md)** - Setup, deployment, troubleshooting, and architecture details
- 👉 **[Project Assets Summary](#project-structure)** - Complete inventory of all project files

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Language** | Python 3.11 |
| **IaC** | AWS CDK v2 |
| **Image AI** | Amazon Rekognition |
| **Compute** | AWS Lambda |
| **Storage** | Amazon S3, DynamoDB |
| **Messaging** | SNS, SQS |
| **Analytics** | Athena, Glue, QuickSight |
| **Config** | SSM Parameter Store |
| **Monitoring** | CloudWatch |

## 🔧 AWS Account Configuration

**Account Details:**
- **AWS Account ID:** `784055307907`
- **IAM User:** `Vinay-AI`
- **Default Region:** `us-east-1`
- **Asset Bucket:** `rekognition-915916`
- **Athena Results Bucket:** `athena-results-784055307907`
- **Image Bucket Prefix:** `sagemaker`
- **QuickSight User:** `Vinay-AI`

**Important:** Update `cdk.json` context keys if using a different AWS account:

```json
{
  "context": {
    "asset_bucket": "your-asset-bucket",
    "image_bucket_prefix": "your-prefix",
    "quicksight_user": "your-quicksight-user"
  }
}
```

## 📊 What Gets Deployed

The CDK app deploys 4 interconnected stacks:

### 1. **APIStack** - Image Ingestion & Upload
**Purpose:** REST API endpoint for image uploads with event-driven S3 integration

**Resources:**
- API Gateway (`GET /?url=<image_url>&name=<filename>`)
- ImageGetAndSaveLambda (30s timeout, downloads and stores images)
- S3 image bucket (`sagemaker-<region>-<account>`)
- SNS topic for image upload events
- SQS upload queue (360s visibility timeout)
- SQS upload DLQ with CloudWatch alarm

**Features:**
- Downloads images from external URLs via HTTP/HTTPS
- Validates image before upload
- Triggers event chain via SNS/SQS
- Error handling with DLQ for failed uploads

### 2. **RekognitionStack** - AI Classification & Storage
**Purpose:** Amazon Rekognition-powered image classification with DynamoDB persistence

**Resources:**
- image_recognition Lambda (300s timeout, polls SQS)
- list_images Lambda (30s timeout, API endpoint)
- DynamoDB Classifications table (on-demand billing, partition key: `image`)
- API Gateway for list endpoint
- Event source mapping from upload queue

**Features:**
- Calls Rekognition DetectLabels API (max 10 labels, 70% confidence)
- Stores results in DynamoDB with timestamp
- Publishes to SNS rekognized topic
- Handles throttling and invalid image errors
- Provides list endpoint for query classification results

### 3. **IntegrationStack** - XML Conversion & Downstream Forwarding
**Purpose:** Convert classification results to XML and forward to downstream systems

**Resources:**
- send_email Lambda (300s timeout, polls SQS)
- SaveXMLLambda (30s timeout, API endpoint)
- SNS rekognized topic
- SQS rekognized queue (1800s visibility timeout)
- SQS rekognized DLQ with CloudWatch alarm
- S3 XML output bucket
- SSM Parameter Store for downstream endpoint URL

**Features:**
- Converts Rekognition results to XML format
- HTTP POST to downstream endpoint (URL from SSM)
- Validates XML structure before storage
- Stores XML payloads in S3 with timestamped keys
- Full error handling and retry logic

### 4. **VisualizationStack** - Analytics & Dashboards
**Purpose:** Federated queries on DynamoDB data with QuickSight visualization

**Resources:**
- Athena DynamoDB connector (SAR Lambda)
- Glue crawler for schema discovery
- Glue database and data catalog
- Athena workgroup (dynamodb-visualization)
- QuickSight data source
- IAM roles with required permissions

**Features:**
- Federated SQL queries on DynamoDB from Athena
- Automatic schema discovery via Glue crawler
- Pre-configured QuickSight integration
- Cost-optimized with S3 result/spill buckets
- Full audit logging via CloudWatch

## 🔒 Security & IAM

- ✅ Complete IAM policy templates included
- ✅ Least-privilege access patterns
- ✅ S3 bucket encryption and SSL enforcement
- ✅ No hardcoded credentials
- ✅ Dead-letter queues for error tracking
- ✅ CloudWatch alarms for monitoring

## 💰 Cost Optimization

- Lambda with optimized memory/timeout settings
- DynamoDB on-demand pricing
- S3 lifecycle policies
- Dead-letter queues to prevent lost messages
- CloudWatch alarms for cost monitoring

## 🛠️ Development

Built using AWS CDK best practices:

- Modular stack architecture
- Cross-stack parameter passing (no CloudFormation exports)
- Context-driven configuration (cdk.json)
- Automated deployment scripts
- Comprehensive error handling
- Workshop format with TODO comments and *_solution.py references

## 📝 Key Design Decisions

- **SQS visibility timeout** - Set to 6× Lambda timeout to prevent duplicates
- **DLQs everywhere** - All queues have dead-letter queues with CloudWatch alarms
- **Bucket retention** - Image bucket and DynamoDB table use RETAIN policy
- **boto3 optimization** - Clients instantiated at module level for connection reuse
- **Logging** - Structured logging with Python logging module
- **Configuration as Code** - All runtime config flows through cdk.json

## Deployment Commands

```bash
# Bash Deployment (Linux/Mac)
cd solution-files/python

# Deploy all stacks
./deploy.sh --region us-east-1

# Deploy single stack
./deploy.sh --stack APIStack --region us-east-1

# Preview changes
./deploy.sh --diff --region us-east-1

# Destroy all stacks
./deploy.sh --destroy --region us-east-1

# Cleanup orphaned resources
./deploy.sh --cleanup --region us-east-1
```

```powershell
# PowerShell Deployment (Windows)
cd solution-files\python

# Deploy all stacks (simple mode)
.\deploy-simple.ps1

# Deploy with specific region
$env:AWS_REGION = "us-east-1"
.\deploy-simple.ps1

# View deployment progress
.\deploy-simple.ps1 -Verbose
```

## 🐛 Troubleshooting

### Image Upload Returns 502
```bash
aws logs tail /aws/lambda/ImageGetAndSaveLambda --follow --region us-east-1
```

### DynamoDB Records Not Appearing
```bash
aws lambda list-event-source-mappings --function-name image_recognition --region us-east-1
```

### QuickSight Dashboard Missing Data
```bash
aws glue start-crawler --name dynamodb-classifications-crawler --region us-east-1
```

See complete troubleshooting guide in the [full documentation](./README.md).

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- Unit tests for Lambda functions
- Integration test suite
- CI/CD pipeline (GitHub Actions)
- Additional Rekognition features (face detection, text extraction)
- Multi-region deployment support

## 📄 License

This project can be used by the curious - all the curious and people who want to build something amazing.

**Free to use for:** Learning, experimentation, and building amazing things


## � Author & Credits

**Project Lead:** Ajit Jadhav  
**Repository:** [github.com/VinayShinde-Cloud/AWS_Rekognition](https://github.com/VinayShinde-Cloud/AWS_Rekognition)

## �🙏 Acknowledgments

- Built with AWS CDK
- Uses Amazon Rekognition for AI-powered image classification
- Inspired by serverless architecture best practices
- Developed using Kiro AI IDE
- Special thanks to Ajit Jadhav for the original architecture design

---

**Last Updated:** July 2026  
**Python Version:** 3.11  
**AWS CDK Version:** 2.118.0  
**Status:** Production-Ready
