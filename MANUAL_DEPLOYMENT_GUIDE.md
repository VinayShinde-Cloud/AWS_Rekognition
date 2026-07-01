# Cloudage Image Rekognition - Manual Deployment Guide

## Overview

This guide provides step-by-step instructions for manually deploying the entire Cloudage Image Rekognition pipeline using PowerShell or bash commands. The solution consists of 4 CDK stacks deployed in dependency order.

---

## Prerequisites

Before starting, ensure you have:

### 1. AWS Account & Credentials
```powershell
# Verify AWS CLI is configured
aws configure

# Verify credentials work
aws sts get-caller-identity
```

**Expected Output:**
```json
{
    "UserId": "AIDAJ...",
    "Account": "784055307907",
    "Arn": "arn:aws:iam::784055307907:user/Vinay-AI"
}
```

### 2. Required Software
```powershell
# Check Python 3.11+
python --version

# Check Node.js 20+
node --version

# Check AWS CDK
npm list -g aws-cdk

# Check AWS CLI v2
aws --version
```

### 3. Python Virtual Environment
```powershell
# Navigate to project directory
cd solution-files\python

# Create virtual environment (if not exists)
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\Activate.ps1

# On Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. AWS Account Configuration
- **Account ID:** `784055307907`
- **Region:** `us-east-1`
- **IAM User:** `Vinay-AI`
- **Asset Bucket:** `rekognition-915916`
- **Athena Results Bucket:** `athena-results-784055307907`

---

## Deployment Methods

### Method 1: Automated Script (Recommended)

Use the PowerShell deployment script for automatic validation and error handling:

#### Deploy All Stacks
```powershell
cd solution-files\python
.\deploy-manual.ps1
```

#### Deploy Single Stack
```powershell
# Deploy APIStack only
.\deploy-manual.ps1 -Stack APIStack

# Deploy IntegrationStack only
.\deploy-manual.ps1 -Stack IntegrationStack

# Deploy RekognitionStack only
.\deploy-manual.ps1 -Stack RekognitionStack

# Deploy VisualizationStack only
.\deploy-manual.ps1 -Stack VisualizationStack
```

#### Preview Changes (Dry Run)
```powershell
.\deploy-manual.ps1 -DiffOnly
```

#### Destroy All Stacks
```powershell
.\deploy-manual.ps1 -Destroy
```

#### Get Help
```powershell
.\deploy-manual.ps1 -Help
```

---

### Method 2: Manual CDK Commands (Step-by-Step)

If you prefer to deploy manually, follow these steps:

#### Step 1: Bootstrap CDK
```powershell
cd solution-files\python

# Bootstrap CDK in your AWS account
cdk bootstrap aws://784055307907/us-east-1 --region us-east-1
```

**Output:**
```
 ✓ Environment aws://784055307907/us-east-1 bootstrapped.
```

#### Step 2: Deploy APIStack
```powershell
# Show changes first
cdk diff APIStack --region us-east-1

# Deploy the stack
cdk deploy APIStack --require-approval never --region us-east-1
```

**Expected Resources:**
- API Gateway REST API
- Lambda: ImageGetAndSaveLambda
- S3 bucket for images
- SNS topic: image_uploaded_topic
- SQS queue: upload_queue
- SQS DLQ: upload_dlq

**Output File:** `cdk-outputs-APIStack.json`

#### Step 3: Deploy IntegrationStack
```powershell
cdk deploy IntegrationStack --require-approval never --region us-east-1
```

**Expected Resources:**
- SNS topic: image_recognized_topic
- SQS queue: rekognized_queue
- SQS DLQ: rekognized_dlq
- Lambda: send_email (integration handler)
- Lambda: SaveXMLLambda (XML storage)
- API Gateway: /save endpoint
- S3 bucket for XML output
- SSM Parameter: endpoint_url

**Output File:** `cdk-outputs-IntegrationStack.json`

#### Step 4: Deploy RekognitionStack
```powershell
cdk deploy RekognitionStack --require-approval never --region us-east-1
```

**Expected Resources:**
- DynamoDB table: Classifications (partition key: image)
- Lambda: image_recognition (Rekognition processor)
- Lambda: ListImagesLambda (list classifications)
- API Gateway: /images endpoint
- Lambda event source mapping (SQS → image_recognition)

**Output File:** `cdk-outputs-RekognitionStack.json`

#### Step 5: Fix S3 Event Notification (Important!)
The S3 bucket event notification may not be created by CDK when the bucket already exists. Create it manually:

```powershell
# Get the SNS topic ARN from APIStack outputs
$snsTopicArn = (aws cloudformation describe-stacks `
    --stack-name APIStack `
    --query "Stacks[0].Outputs[?OutputKey=='ImageUploadTopicArn'].OutputValue" `
    --output text `
    --region us-east-1)

Write-Host "SNS Topic ARN: $snsTopicArn"

# Create notification configuration file
$notificationConfig = @{
    TopicConfigurations = @(
        @{
            Id = "ImageUploadNotification"
            TopicArn = $snsTopicArn
            Events = @("s3:ObjectCreated:Put")
        }
    )
} | ConvertTo-Json

# Apply notification configuration
aws s3api put-bucket-notification-configuration `
    --bucket "sagemaker-us-east-1-784055307907" `
    --notification-configuration $notificationConfig `
    --region us-east-1

Write-Host "S3 event notification configured successfully"
```

#### Step 6: Deploy VisualizationStack
```powershell
cdk deploy VisualizationStack --require-approval never --region us-east-1
```

**Expected Resources:**
- S3 bucket: athena-spill (for Athena connector spill)
- S3 bucket: athena-results-784055307907 (for query results)
- Athena workgroup: dynamodb-visualization
- Athena data catalog: recognitiondb (federated query)
- Lambda: Athena DynamoDB connector (via SAR)
- Glue database: recognitiondb
- Glue crawler: dynamodb-classifications-crawler
- QuickSight data source: DynamoDB via Athena
- IAM roles with appropriate permissions

**Output File:** `cdk-outputs-VisualizationStack.json`

---

## Post-Deployment Setup

After all stacks are deployed, complete these steps:

### 1. Start Glue Crawler
The Glue crawler discovers schema from DynamoDB and populates the Glue Data Catalog:

```powershell
# Start the crawler
aws glue start-crawler `
    --name dynamodb-classifications-crawler `
    --region us-east-1

# Monitor crawler status
aws glue get-crawler `
    --name dynamodb-classifications-crawler `
    --region us-east-1 `
    --query "Crawler.[State,LastCrawl.Status]"
```

**Wait 2-5 minutes for the crawler to complete.**

### 2. Verify DynamoDB Table
```powershell
# Get the table name
$tableName = (Get-Content cdk-outputs-RekognitionStack.json | ConvertFrom-Json).RekognitionStack.ClassificationsTableName

Write-Host "DynamoDB Table: $tableName"

# Verify table structure
aws dynamodb describe-table `
    --table-name $tableName `
    --region us-east-1 `
    --query "Table.[TableStatus,BillingModeSummary.BillingMode,ItemCount]"
```

### 3. Verify Athena Setup
```powershell
# Check Athena workgroup
aws athena get-work-group `
    --work-group dynamodb-visualization `
    --region us-east-1 `
    --query "WorkGroup.[State,Configuration.ResultConfigurationUpdates.OutputLocation]"

# List databases in Glue catalog
aws glue get-databases `
    --region us-east-1 `
    --query "DatabaseList[*].Name"
```

### 4. (Optional) Configure QuickSight
```powershell
# List QuickSight data sources
aws quicksight list-data-sources `
    --aws-account-id 784055307907 `
    --region us-east-1
```

Then manually:
1. Log into AWS Console: https://console.aws.amazon.com/quicksight
2. Go to "Manage data" → "Data sources"
3. Create a new dashboard using the "DynamoDB via Athena" data source

---

## Testing the Pipeline

### 1. Upload Test Images
```powershell
cd solution-files\python

# Send 5 test vehicle images
python send_images.py

# When prompted, enter: 5

# When prompted, enter: yes
```

### 2. Monitor Processing
```powershell
# Wait 30-60 seconds for Lambda to process

# Scan DynamoDB to see results
python scan_classifications.py --region us-east-1

# Expected output:
# ════════════════════════════════════════════════════════════════
#   Rekognition Classifications — RekognitionStack-Classifications...
#   Items returned: 5
# ════════════════════════════════════════════════════════════════
#   [1] car-001.jpg
#       Labels : ['Transportation', 'Vehicle', 'Car', ...]
```

### 3. Check CloudWatch Logs
```powershell
# Check image_recognition Lambda logs
aws logs tail /aws/lambda/image_recognition --follow --region us-east-1

# Check send_email Lambda logs (if integration is configured)
aws logs tail /aws/lambda/send_email --follow --region us-east-1

# Check ListImagesLambda logs
aws logs tail /aws/lambda/ListImagesLambda --follow --region us-east-1
```

### 4. Test API Endpoints
```powershell
# Get API endpoint from outputs
$apiEndpoint = (Get-Content cdk-outputs-APIStack.json | ConvertFrom-Json).APIStack.RESTAPIEndpoint0F9F3858

# Test image upload API
$imageUrl = "https://example.com/test-image.jpg"
$response = curl.exe -s "$apiEndpoint`?url=$([System.Uri]::EscapeDataString($imageUrl))&name=test.jpg"
Write-Host "Upload Response: $response"

# Get list of classifications
$listEndpoint = (Get-Content cdk-outputs-RekognitionStack.json | ConvertFrom-Json).RekognitionStack.RESTAPIEndpoint0F9F3858
$classifications = curl.exe -s "$listEndpoint"
Write-Host "Classifications: $classifications"
```

---

## Troubleshooting

### Issue: S3 Event Notification Not Working

**Symptom:** Images upload successfully but DynamoDB remains empty.

**Solution:**
```powershell
# Verify S3 notification configuration
aws s3api get-bucket-notification-configuration `
    --bucket "sagemaker-us-east-1-784055307907" `
    --region us-east-1

# If empty or wrong, reconfigure using the script in Step 5 above
```

### Issue: Lambda Not Triggering

**Symptom:** SQS queue has messages but Lambda isn't processing them.

**Solution:**
```powershell
# Check Lambda event source mapping
aws lambda list-event-source-mappings `
    --function-name image_recognition `
    --region us-east-1 `
    --query "EventSourceMappings[*].[State,EventSourceArn]"

# If not enabled, manually create:
aws lambda create-event-source-mapping `
    --event-source-arn "arn:aws:sqs:us-east-1:784055307907:APIStack-uploadedimagequeue43D6CD3D-nkTU7aynvOOf" `
    --function-name image_recognition `
    --batch-size 1 `
    --region us-east-1
```

### Issue: Athena Query Fails - Permission Denied

**Symptom:** "Access denied when writing output to S3 bucket"

**Solution:**
```powershell
# Verify Athena results bucket has correct permissions
aws s3api get-bucket-policy `
    --bucket "athena-results-784055307907" `
    --region us-east-1

# Check that athena.amazonaws.com and quicksight.amazonaws.com service principals have access
```

### Issue: Glue Crawler Fails

**Symptom:** Crawler status shows FAILED

**Solution:**
```powershell
# Check crawler logs
aws logs describe-log-groups `
    --log-group-name-prefix "/aws-glue/crawlers" `
    --region us-east-1

# Re-run the crawler
aws glue start-crawler `
    --name dynamodb-classifications-crawler `
    --region us-east-1
```

### Issue: QuickSight Data Source Not Found

**Symptom:** "Resource of type 'AWS::QuickSight::DataSource' with identifier 'dynamodb-athena-datasource' was not found"

**Solution:**
1. Ensure QuickSight is subscribed in the account:
   ```powershell
   aws quicksight list-users `
       --aws-account-id 784055307907 `
       --namespace default `
       --region us-east-1
   ```

2. If not subscribed, subscribe in AWS Console:
   - Go to https://console.aws.amazon.com/quicksight
   - Click "Sign up for QuickSight"
   - Choose Standard or Enterprise edition

3. Re-deploy VisualizationStack after subscribing

---

## Stack Destruction

To clean up and remove all resources:

```powershell
# Destroy all stacks (reverse order)
.\deploy-manual.ps1 -Destroy

# Or manually, one by one (reverse order):
cdk destroy VisualizationStack --force --region us-east-1
cdk destroy RekognitionStack --force --region us-east-1
cdk destroy IntegrationStack --force --region us-east-1
cdk destroy APIStack --force --region us-east-1
```

**Note:** Resources with RemovalPolicy.RETAIN (DynamoDB, S3 buckets) will NOT be deleted. Delete them manually if needed.

---

## Deployment Summary

| Stack | Resources | Status |
|-------|-----------|--------|
| **APIStack** | API Gateway, Lambda, S3, SNS, SQS | ✅ Deployed |
| **IntegrationStack** | SNS, SQS, Lambda, API Gateway, SSM | ✅ Deployed |
| **RekognitionStack** | DynamoDB, Lambda, API Gateway | ✅ Deployed |
| **VisualizationStack** | Athena, Glue, QuickSight, S3, IAM | ✅ Deployed |

---

## Quick Reference Commands

```powershell
# Deploy everything
.\deploy-manual.ps1

# Deploy single stack
.\deploy-manual.ps1 -Stack APIStack

# Dry run
.\deploy-manual.ps1 -DiffOnly

# Destroy everything
.\deploy-manual.ps1 -Destroy

# Manual CDK commands
cdk bootstrap aws://784055307907/us-east-1 --region us-east-1
cdk deploy APIStack --require-approval never --region us-east-1
cdk deploy IntegrationStack --require-approval never --region us-east-1
cdk deploy RekognitionStack --require-approval never --region us-east-1
cdk deploy VisualizationStack --require-approval never --region us-east-1

# Post-deployment
aws glue start-crawler --name dynamodb-classifications-crawler --region us-east-1

# Testing
python send_images.py
python scan_classifications.py --region us-east-1

# Verification
aws sts get-caller-identity
aws s3 ls s3://rekognition-915916 --region us-east-1
aws dynamodb list-tables --region us-east-1
aws lambda list-functions --region us-east-1

# Clean up
cdk destroy --all --force --region us-east-1
```

---

## Support & Documentation

- **AWS CDK Docs:** https://docs.aws.amazon.com/cdk/
- **Rekognition API:** https://docs.aws.amazon.com/rekognition/latest/dg/
- **DynamoDB:** https://docs.aws.amazon.com/dynamodb/
- **Athena Connector:** https://aws.amazon.com/blogs/big-data/visualize-amazon-dynamodb-insights-in-amazon-quicksight-using-the-amazon-athena-dynamodb-connector-and-aws-glue/

---

**Last Updated:** July 1, 2026  
**Account ID:** 784055307907  
**Region:** us-east-1  
**IAM User:** Vinay-AI
