# 🚀 AWS Rekognition - Serverless Image Processing Pipeline

> **Production-grade, event-driven image recognition platform built with AWS CDK, Amazon Rekognition, Lambda, DynamoDB, S3, SNS, SQS, Athena, and QuickSight.**

![AWS](https://img.shields.io/badge/AWS-Cloud-orange)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![CDK](https://img.shields.io/badge/AWS%20CDK-v2-success)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)

---

# 📌 Project Overview

This project demonstrates a **production-ready serverless image processing pipeline** that automatically analyzes images using **Amazon Rekognition**, stores metadata in **Amazon DynamoDB**, distributes events through **SNS/SQS**, integrates with downstream applications, and provides analytical dashboards using **Athena**, **AWS Glue**, and **Amazon QuickSight**.

The entire infrastructure is deployed using **AWS CDK (Infrastructure as Code)**, making the solution repeatable, scalable, secure, and easy to maintain.

---

# 🎯 Business Use Cases

This solution can be adapted for enterprise workloads such as:

* 📷 Smart Image Classification
* 🏢 Digital Asset Management
* 🚗 Vehicle Recognition
* 👤 Identity Verification
* 🏥 Medical Image Processing
* 🛒 Retail Product Recognition
* 🔒 Security & Surveillance
* 📦 Inventory Automation

---

# 🏗 Solution Architecture

![AWS Rekognition Architecture](https://raw.githubusercontent.com/VinayShinde-Cloud/AWS_Rekognition/main/Concepts/Recognition.drawio.png)

---

# ⚙️ Architecture Workflow

1. A user uploads an image through the REST API.
2. Amazon API Gateway invokes AWS Lambda.
3. The image is securely stored in Amazon S3.
4. Amazon Rekognition analyzes the image.
5. Labels, confidence scores, and metadata are saved into DynamoDB.
6. SNS publishes processing events.
7. SQS buffers downstream workloads.
8. Integration Lambda converts metadata into XML.
9. Data is queried through Athena.
10. Amazon QuickSight provides interactive dashboards.

---

# ☁️ AWS Services Used

| Service            | Purpose                   |
| ------------------ | ------------------------- |
| Amazon API Gateway | REST API Endpoint         |
| AWS Lambda         | Serverless Compute        |
| Amazon Rekognition | AI Image Recognition      |
| Amazon S3          | Image Storage             |
| Amazon DynamoDB    | Metadata Storage          |
| Amazon SNS         | Event Notifications       |
| Amazon SQS         | Message Queue             |
| AWS IAM            | Security & Access Control |
| AWS CloudWatch     | Monitoring                |
| AWS Glue           | Data Catalog              |
| Amazon Athena      | SQL Analytics             |
| Amazon QuickSight  | Dashboards                |
| AWS CDK            | Infrastructure as Code    |

---

# ✨ Key Features

* Fully Serverless Architecture
* Event-Driven Processing
* Infrastructure as Code (AWS CDK)
* Production-Ready IAM Policies
* Highly Scalable Design
* Dead Letter Queue Support
* Fault Tolerant Processing
* Secure Resource Access
* Real-Time Image Analysis
* Analytics Dashboard
* Modular CDK Stacks
* Easy Deployment

---

# 📂 Project Structure

```text
AWS_Rekognition/
│
├── Concepts/
│   └── Recognition.drawio.png
│
├── Examples/
│
├── Policies/
│
├── QuickSightFixes/
│
└── solution-files/
    └── python/
        ├── api/
        ├── recognition/
        ├── integration/
        ├── visualization/
        ├── iam/
        ├── app.py
        ├── deploy.sh
        └── deploy-simple.ps1
```

---

# 🏗 CDK Stack Overview

| Stack              | Description                           |
| ------------------ | ------------------------------------- |
| APIStack           | API Gateway, Lambda, S3, SNS, SQS     |
| RekognitionStack   | Amazon Rekognition & DynamoDB         |
| IntegrationStack   | XML Transformation & Event Forwarding |
| VisualizationStack | Athena, Glue & QuickSight             |

---

# 🚀 Quick Start

## Clone Repository

```bash
git clone https://github.com/VinayShinde-Cloud/AWS_Rekognition.git

cd AWS_Rekognition/solution-files/python
```

---

## Create Virtual Environment

### Linux / macOS

```bash
python3 -m venv .venv

source .venv/bin/activate
```

### Windows

```powershell
python -m venv .venv

.venv\Scripts\Activate.ps1
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Deploy Infrastructure

### Linux

```bash
./deploy.sh --region us-east-1
```

### Windows

```powershell
.\deploy-simple.ps1
```

---

## Test API

```bash
curl "https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/?url=https://example.com/image.jpg&name=test.jpg"
```

---

# 🔄 Deployment Commands

Deploy All Stacks

```bash
./deploy.sh --region us-east-1
```

Deploy Individual Stack

```bash
./deploy.sh --stack APIStack
```

Preview Changes

```bash
./deploy.sh --diff
```

Destroy Infrastructure

```bash
./deploy.sh --destroy
```

Cleanup Resources

```bash
./deploy.sh --cleanup
```

---

# 🔒 Security Features

* Least Privilege IAM Policies
* Resource-Based Access Control
* Encrypted Storage
* Secure Lambda Permissions
* Dead Letter Queues
* CloudWatch Monitoring
* Event Retry Mechanism

---

# 📊 Monitoring

The project integrates with:

* Amazon CloudWatch Logs
* CloudWatch Metrics
* CloudWatch Alarms
* AWS X-Ray (Optional)

---

# 🛠 Technology Stack

| Category       | Technology                   |
| -------------- | ---------------------------- |
| Programming    | Python 3.11                  |
| Infrastructure | AWS CDK v2                   |
| AI             | Amazon Rekognition           |
| Storage        | Amazon S3                    |
| Database       | Amazon DynamoDB              |
| Messaging      | Amazon SNS, Amazon SQS       |
| Analytics      | Athena, AWS Glue, QuickSight |
| Monitoring     | CloudWatch                   |
| Security       | IAM                          |

---

# 📈 Future Enhancements

* Amazon Bedrock Integration
* Face Recognition
* Custom Rekognition Labels
* Multi-Region Deployment
* CI/CD using GitHub Actions
* Docker Support
* Terraform Version
* CloudFormation Templates

---

# 👨‍💻 Author

**Vinay Shinde**

Generative AI Engineer 

GitHub Repository:

https://github.com/VinayShinde-Cloud/AWS_Rekognition

---

# 📄 License

This project is available for educational purposes, learning, experimentation, and portfolio demonstrations.

---

## ⭐ If you found this project helpful, consider giving it a Star on GitHub!
