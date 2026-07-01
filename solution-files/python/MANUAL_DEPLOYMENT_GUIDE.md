# Manual Deployment Guide — Cloudage Image Rekognition Pipeline

## Overview

This guide provides step-by-step instructions for manually deploying the AWS Rekognition pipeline using AWS CDK. The system consists of 4 interdependent CloudFormation stacks that must be deployed in a specific order.

---

## Prerequisites

Before starting deployment, ensure the following are installed and configured:

### 1. AWS CLI v2
```bash
# Verify installation
aws --version

# Configure credentials
aws configure
# Enter:
# - AWS Access Key ID: [your-access-key]
# - AWS Secret Access Key: [your-secret-key]
# - Default region: us-east-1
# - Default output format: json
```

**Reference:** https://aws.amazon.com/cli/

### 2. Python 3.11+
```bash
# Verify installation
python --version

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\Activate.ps1
# On Linux/Mac:
source .venv/bin/activate
```

### 3. Node.js 20+
```bash
# Verify installation
node --version
npm --version
```

**Reference:** https://nodejs.org/

### 4. AWS CDK CLI
```bash
# Install globally
npm install -g aws-cdk

# Verify installation
cdk --version
```

### 5. Python Dependencies
```bash
# Install requirements (with venv activated)
pip install -r requirements.txt
```

---

## Account & Region Configuration

| Property | Value | Notes |
|----------|-------|-------|
| AWS Account ID | 784055307907 | Used for ARNs and S3 bucket naming |
| Region | us-east-1 | Primary deployment region |
| IAM User | Vinay-AI | Deploying user account |
| Asset Bucket | rekognition-915916 | Stores Lambda layer ZIP |
| Athena Results Bucket | athena-results-784055307907 | Query results storage |

---

## Deployment Order

Stacks **MUST** be deployed in this exact order. Each stack depends on outputs from previous stacks:

```
1. APIStack
   ├─ Creates: S3 image bucket, API Gateway, Lambda, SNS topic, SQS queue
   ├─ Outputs: API endpoint, SQS URL/ARN, SNS topic ARN
   └─ Time: ~5-7 minutes

2. IntegrationStack
   ├─ Requires: SNS topic ARN from APIStack
   ├─ Creates: SNS subscriptions, SQS queues, Lambda functions
   ├─ Outputs: SNS topic ARN for downstream, API endpoint
   └─ Time: ~5-7 minutes

3. RekognitionStack
   ├─ Requires: SQS URL/ARN from APIStack, SNS topic ARN from IntegrationStack
   ├─ Creates: DynamoDB table, Lambda event mappings, API for list images
   ├─ Outputs: DynamoDB table name/ARN
   └─ Time: ~5-7 minutes

4. VisualizationStack
   ├─ Requires: DynamoDB table name/ARN from RekognitionStack
   ├─ Creates: Athena connector, Glue crawler, QuickSight data source
   ├─ Outputs: Athena workgroup, Glue crawler name
   └─ Time: ~10-15 minutes (includes SAR app deployment)
```

---

## Step 1: CDK Bootstrap

Bootstrap the CDK environment in your AWS account. This creates the necessary CloudFormation resources for CDK deployments.

```bash
cd solution-files/python

# Activate virtual environment (if not already active)
.venv\Scripts\Activate.ps1

# Bootstrap CDK
cdk bootstrap aws://784055307907/us-east-1 --region us-east-1
```

**Expected Output:**
```
CDKToolkit: creating CloudFormation changeset...
[████████████████] (3/3)

 ✅  Environment aws://784055307907/us-east-1 bootstrapped.
```

---

## Step 2: Deploy APIStack

The API Gateway and image ingestion layer.

```bash
cd solution-files/python

# Preview changes
cdk diff APIStack --region us-east-1

# Deploy stack
cdk deploy APIStack --require-approval never --region us-east-1
```

**What Gets Created:**
- S3 bucket: `sagemaker-us-east-1-784055307907`
- API Gateway endpoint with GET endpoint
- Lambda: `ImageGetAndSaveLambda`
- SNS topic: `APIStack-uploadedimagetopic*`
- SQS queue: `APIStack-uploadedimagequeue*`
- SQS DLQ: `APIStack-UploadImageDLQ*`

**Expected Duration:** 5-7 minutes

**Verify Deployment:**
```bash
# Check CloudFormation stack status
aws cloudformation describe-stacks --stack-name APIStack --query 'Stacks[0].StackStatus' --region us-east-1

# Should output: CREATE_COMPLETE
```

---

## Step 3: Deploy IntegrationStack

The downstream integration layer (XML conversion, HTTP forwarding).

```bash
cd solution-files/python

# Preview changes
cdk diff IntegrationStack --region us-east-1

# Deploy stack
cdk deploy IntegrationStack --require-approval never --region us-east-1
```

**What Gets Created:**
- SNS topic: `IntegrationStack-rekognizedimagetopic*`
- SQS queue: `IntegrationStack-rekognizedimagequeue*`
- SQS DLQ: `IntegrationStack-rekognizedImageDLQ*`
- Lambda: `send_email` (polls SQS, converts to XML, forwards HTTP)
- Lambda: `SaveXMLLambda` (receives XML POST, saves to S3)
- S3 bucket for XML output
- API Gateway endpoint for SaveXMLLambda

**Expected Duration:** 5-7 minutes

**Verify Deployment:**
```bash
aws cloudformation describe-stacks --stack-name IntegrationStack --query 'Stacks[0].StackStatus' --region us-east-1

# Should output: CREATE_COMPLETE
```

---

## Step 4: Deploy RekognitionStack

The image classification layer (Rekognition, DynamoDB).

```bash
cd solution-files/python

# Preview changes
cdk diff RekognitionStack --region us-east-1

# Deploy stack
cdk deploy RekognitionStack --require-approval never --region us-east-1
```

**What Gets Created:**
- DynamoDB table: `RekognitionStack-Classifications*`
- Lambda: `image_recognition` (calls Rekognition, writes to DynamoDB)
- Lambda: `ListImagesLambda` (scans DynamoDB)
- API Gateway endpoint for listing images
- Event source mapping between SQS and Lambda

**Expected Duration:** 5-7 minutes

**Verify Deployment:**
```bash
aws cloudformation describe-stacks --stack-name RekognitionStack --query 'Stacks[0].StackStatus' --region us-east-1

# Should output: CREATE_COMPLETE
```

---

## Step 5: Deploy VisualizationStack

The analytics and visualization layer (Athena, Glue, QuickSight).

```bash
cd solution-files/python

# Preview changes
cdk diff VisualizationStack --region us-east-1

# Deploy stack
cdk deploy VisualizationStack --require-approval never --region us-east-1
```

**What Gets Created:**
- S3 bucket: `athena-results-784055307907` (query results)
- S3 bucket: `athena-spill-*` (temporary large result sets)
- Athena workgroup: `dynamodb-visualization`
- Glue database: `recognitiondb`
- Glue crawler: `dynamodb-classifications-crawler`
- Athena data catalog backed by DynamoDB connector
- QuickSight data source (requires manual subscription in Console)
- Lambda function deployed via SAR (Serverless Application Repository)

**Expected Duration:** 10-15 minutes (includes SAR app deployment)

**Verify Deployment:**
```bash
aws cloudformation describe-stacks --stack-name VisualizationStack --query 'Stacks[0].StackStatus' --region us-east-1

# Should output: CREATE_COMPLETE
```

---

## Post-Deployment Setup

### 1. Manual S3 Event Notification Configuration

If the S3 event notification wasn't created automatically, configure it manually:

```bash
# Create notification configuration
$notificationConfig = @{
    TopicConfigurations = @(
        @{
            Id = "ImageUploadNotification"
            TopicArn = "arn:aws:sns:us-east-1:784055307907:APIStack-uploadedimagetopic*"
            Events = @("s3:ObjectCreated:Put")
        }
    )
} | ConvertTo-Json

# Apply to S3 bucket
aws s3api put-bucket-notification-configuration `
    --bucket sagemaker-us-east-1-784055307907 `
    --notification-configuration $notificationConfig `
    --region us-east-1
```

**Verify:**
```bash
aws s3api get-bucket-notification-configuration `
    --bucket sagemaker-us-east-1-784055307907 `
    --region us-east-1
```

### 2. Start Glue Crawler

The Glue crawler discovers schema from DynamoDB and populates the Data Catalog. This is required for Athena queries.

```bash
# Start crawler
aws glue start-crawler \
    --name dynamodb-classifications-crawler \
    --region us-east-1
```

**Monitor Crawler Progress:**
```bash
# Check crawler status (wait for READY state)
aws glue get-crawler \
    --name dynamodb-classifications-crawler \
    --region us-east-1 \
    --query 'Crawler.State'

# View crawler run history
aws glue get-crawler-metrics \
    --crawler-name dynamodb-classifications-crawler \
    --region us-east-1
```

**Expected Duration:** 2-5 minutes

### 3. (Optional) Setup QuickSight Subscription

QuickSight requires a subscription to your AWS account. If not already done:

1. Open AWS Console: https://console.aws.amazon.com/quicksight
2. Sign up for QuickSight Standard or Enterprise edition
3. Create a user with the username from `cdk.json` (`quicksight_user`, default: `gen-ai-user`)

---

## Testing the Pipeline

### 1. Upload Test Images

Send images through the pipeline using the provided utility script:

```bash
cd solution-files/python

# Send 1 test image
python send_images.py

# Respond with count (1-25) and confirm

# Or send all 25 images at once
echo "25" | echo "yes" | python send_images.py
```

### 2. Verify S3 Upload

```bash
# Check if images are in S3
aws s3 ls s3://sagemaker-us-east-1-784055307907/ --region us-east-1

# Count objects
aws s3 ls s3://sagemaker-us-east-1-784055307907/ --region us-east-1 | wc -l
```

### 3. Monitor SQS Queue

```bash
# Check if messages are being processed
aws sqs get-queue-attributes \
    --queue-url https://sqs.us-east-1.amazonaws.com/784055307907/APIStack-uploadedimagequeue* \
    --attribute-names ApproximateNumberOfMessages \
    --region us-east-1
```

### 4. Verify DynamoDB Results

```bash
cd solution-files/python

# Scan DynamoDB table
python scan_classifications.py --region us-east-1

# Expected output shows 25 items with Rekognition labels
```

### 5. Check CloudWatch Logs

Monitor Lambda execution:

```bash
# Tail image_recognition Lambda logs (real-time)
aws logs tail /aws/lambda/image_recognition --follow --region us-east-1

# Tail send_email Lambda logs
aws logs tail /aws/lambda/send_email --follow --region us-east-1

# Tail SaveXMLLambda logs
aws logs tail /aws/lambda/SaveXMLLambda --follow --region us-east-1
```

---

## Deployed Resources Summary

After successful deployment, the following resources are available:

### API Endpoints

| Endpoint | Purpose | Method |
|----------|---------|--------|
| `https://m49kzeceb2.execute-api.us-east-1.amazonaws.com/prod/` | Upload image | GET `?url=<image_url>&name=<filename>` |
| `https://c08fqhint7.execute-api.us-east-1.amazonaws.com/prod/` | List classifications | GET `/` |
| `https://1czeh1y9i4.execute-api.us-east-1.amazonaws.com/prod/` | Save XML payload | POST `/save` |

### DynamoDB Table

| Property | Value |
|----------|-------|
| Table Name | `RekognitionStack-Classifications0C921F6C-V6CZOJO8NE0J` |
| Partition Key | `image` (String) |
| Billing Mode | On-Demand (auto-scaling) |
| Items | 25 test images (after pipeline execution) |

### Athena Resources

| Resource | Value |
|----------|-------|
| Workgroup | `dynamodb-visualization` |
| Data Catalog | `recognitiondb` (Athena federated catalog) |
| Database | `recognitiondb` (Glue) |
| Results Bucket | `s3://athena-results-784055307907/` |
| Spill Bucket | `s3://athena-spill-*/` |

### Lambda Functions

| Function | Runtime | Trigger | Timeout |
|----------|---------|---------|---------|
| `ImageGetAndSaveLambda` | Python 3.11 | API Gateway | 30s |
| `image_recognition` | Python 3.11 | SQS queue | 300s |
| `ListImagesLambda` | Python 3.11 | API Gateway | 30s |
| `send_email` | Python 3.11 | SQS queue | 300s |
| `SaveXMLLambda` | Python 3.11 | API Gateway | 300s |
| `AthenaDynamoDBConnector` | Java | Athena federated query | 900s |

---

## Troubleshooting

### Issue: "NoSuchBucket" error during deployment

**Cause:** Asset bucket not found or inaccessible

**Solution:**
```bash
# Verify bucket exists
aws s3 ls s3://rekognition-915916/ --region us-east-1

# Verify Lambda layer ZIP is present
aws s3 ls s3://rekognition-915916/ --region us-east-1 | grep requests_layer

# Upload layer ZIP if missing
aws s3 cp requests_layer3_11.zip s3://rekognition-915916/ --region us-east-1
```

### Issue: "QuickSight DataSource" not found error

**Cause:** QuickSight not subscribed or user not created

**Solution:**
1. Subscribe to QuickSight in AWS Console
2. Create a user matching `quicksight_user` in `cdk.json`
3. Redeploy: `cdk deploy VisualizationStack --require-approval never`

### Issue: DynamoDB table remains empty after uploading images

**Cause:** S3 event notification not configured or Lambda not triggered

**Solution:**
1. Manually configure S3 event notification (see Post-Deployment Setup)
2. Check Lambda event source mapping:
   ```bash
   aws lambda list-event-source-mappings \
       --function-name image_recognition \
       --region us-east-1
   ```
3. Check CloudWatch logs for Lambda errors
4. Manually trigger Lambda for testing

### Issue: Athena "Access Denied" when querying

**Cause:** IAM permissions not properly configured for Athena workgroup

**Solution:**
```bash
# Verify QuickSight service role has Athena permissions
aws iam list-attached-role-policies \
    --role-name aws-quicksight-service-role-v0 \
    --region us-east-1

# Attach AWSQuicksightAthenaAccess if missing
aws iam attach-role-policy \
    --role-name aws-quicksight-service-role-v0 \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSQuicksightAthenaAccess
```

---

## Destroying Stacks

To remove all resources and stop incurring costs:

```bash
# Destroy in reverse order (VisualizationStack first)
cdk destroy VisualizationStack --force --region us-east-1
cdk destroy RekognitionStack --force --region us-east-1
cdk destroy IntegrationStack --force --region us-east-1
cdk destroy APIStack --force --region us-east-1

# Or destroy all at once
cdk destroy --force --region us-east-1
```

**Note:** S3 buckets and DynamoDB tables have `RemovalPolicy.RETAIN` set, so they survive stack deletion for data safety.

---

## Cost Estimation

| Service | Per Image | Per 25 Images | Estimate |
|---------|-----------|---------------|----------|
| Rekognition DetectLabels | $0.001 | $0.025 | $0.025 |
| Lambda invocations | ~$0.0002 | ~$0.005 | $0.005 |
| DynamoDB writes | ~$0.000001 | ~$0.000025 | $0.000025 |
| S3 storage (per month) | — | ~50 KB | ~$0.001 |
| Athena queries | $5 per TB scanned | ~1 MB | ~$0.000005 |
| **Total (25 images)** | — | — | **~$0.03** |

---

## Next Steps

1. ✅ Deploy all 4 stacks (completed above)
2. ✅ Configure S3 event notifications (post-deployment setup)
3. ✅ Start Glue crawler (post-deployment setup)
4. ✅ Test pipeline with sample images (testing section)
5. 🔲 (Optional) Create QuickSight dashboards in AWS Console
6. 🔲 (Optional) Set up SNS notifications for Lambda errors
7. 🔲 (Optional) Configure CloudWatch alarms for SQS DLQs

---

## Support & References

- **AWS CDK Documentation:** https://docs.aws.amazon.com/cdk/
- **AWS CLI Documentation:** https://docs.aws.amazon.com/cli/
- **AWS Rekognition:** https://docs.aws.amazon.com/rekognition/
- **Amazon Athena DynamoDB Connector:** https://serverlessrepo.aws.amazon.com/applications
- **QuickSight:** https://docs.aws.amazon.com/quicksight/

---

## Appendix: Environment Variables

Configure these in your shell for convenience:

```bash
# Windows PowerShell
$env:AWS_REGION = "us-east-1"
$env:AWS_ACCOUNT = "784055307907"
$env:QUICKSIGHT_USER = "gen-ai-user"

# Linux/Mac
export AWS_REGION=us-east-1
export AWS_ACCOUNT=784055307907
export QUICKSIGHT_USER=gen-ai-user
```

Then use in commands:
```bash
cdk deploy --region $AWS_REGION
aws s3 ls --region $AWS_REGION
```

---

**Last Updated:** July 1, 2026  
**Version:** 1.0
