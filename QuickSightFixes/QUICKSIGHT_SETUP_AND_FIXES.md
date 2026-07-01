# QuickSight Setup & Fixes - Comprehensive Guide

## Overview

This document consolidates all QuickSight setup, configuration, and troubleshooting information for the Cloudage Image Rekognition pipeline.

---

## Table of Contents

1. [Quick Setup](#quick-setup)
2. [Prerequisites](#prerequisites)
3. [Step-by-Step Configuration](#step-by-step-configuration)
4. [Common Issues & Fixes](#common-issues--fixes)
5. [Advanced Configuration](#advanced-configuration)
6. [Testing & Verification](#testing--verification)
7. [Troubleshooting Commands](#troubleshooting-commands)

---

## Quick Setup

### 1. Subscribe QuickSight (If Not Already Done)

```powershell
# Check if QuickSight is subscribed
aws quicksight list-users `
    --aws-account-id 784055307907 `
    --namespace default `
    --region us-east-1
```

**If error "Subscription does not exist":**
- Go to: https://console.aws.amazon.com/quicksight
- Click "Sign up for QuickSight"
- Choose edition (Standard $18/mo or Enterprise $25/user/mo)
- Complete subscription

### 2. Create QuickSight User (If Not Done)

```powershell
# Create author user
aws quicksight register-user `
    --aws-account-id 784055307907 `
    --namespace default `
    --identity-type IAM `
    --iam-arn "arn:aws:iam::784055307907:user/Vinay-AI" `
    --email "vinay@example.com" `
    --user-role AUTHOR `
    --region us-east-1
```

### 3. Deploy VisualizationStack

```powershell
cd solution-files\python
cdk deploy VisualizationStack --require-approval never --region us-east-1
```

### 4. Start Glue Crawler

```powershell
aws glue start-crawler --name dynamodb-classifications-crawler --region us-east-1
```

### 5. Create QuickSight Data Source

```powershell
aws quicksight create-data-source `
    --aws-account-id 784055307907 `
    --data-source-id dynamodb-athena-datasource `
    --name "DynamoDB via Athena" `
    --type ATHENA `
    --data-source-parameters '{"AthenaParameters":{"WorkGroup":"dynamodb-visualization"}}' `
    --region us-east-1
```

---

## Prerequisites

### Requirements Checklist

- [ ] AWS Account with us-east-1 region
- [ ] Account ID: `784055307907`
- [ ] IAM User: `Vinay-AI` with appropriate permissions
- [ ] QuickSight subscription (Standard or Enterprise)
- [ ] All 3 previous stacks deployed (APIStack, IntegrationStack, RekognitionStack)
- [ ] Python venv activated
- [ ] AWS CLI v2 configured
- [ ] CDK CLI installed

### Required Permissions

**IAM User must have:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "quicksight:*",
        "athena:*",
        "glue:*",
        "s3:*",
        "dynamodb:*",
        "iam:*"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Step-by-Step Configuration

### Step 1: Verify VisualizationStack Deployment

```powershell
# Check stack status
aws cloudformation describe-stacks `
    --stack-name VisualizationStack `
    --region us-east-1 `
    --query "Stacks[0].[StackStatus,StackName]"

# Expected output: CREATE_COMPLETE | VisualizationStack
```

### Step 2: Verify Glue Resources

```powershell
# Check Glue database
aws glue get-database --name recognitiondb --region us-east-1

# Check Glue crawler
aws glue get-crawler --name dynamodb-classifications-crawler --region us-east-1

# Check crawler status (should be READY)
aws glue get-crawler `
    --name dynamodb-classifications-crawler `
    --region us-east-1 `
    --query "Crawler.State"
```

### Step 3: Start Glue Crawler (Schema Discovery)

```powershell
# Start crawler
aws glue start-crawler --name dynamodb-classifications-crawler --region us-east-1

# Monitor progress
for ($i=0; $i -lt 5; $i++) {
    aws glue get-crawler `
        --name dynamodb-classifications-crawler `
        --region us-east-1 `
        --query "Crawler.[State,LastCrawl.Status]"
    Start-Sleep -Seconds 30
}

# Should eventually show: READY | SUCCEEDED
```

### Step 4: Verify Athena Setup

```powershell
# Check Athena workgroup
aws athena get-work-group --work-group dynamodb-visualization --region us-east-1

# Check Athena data catalog
aws athena list-data-catalogs --region us-east-1 --query "DataCatalogsSummary[*]"

# Test Athena query
aws athena start-query-execution `
    --query-string "SELECT * FROM recognitiondb.classifications LIMIT 5" `
    --work-group dynamodb-visualization `
    --region us-east-1
```

### Step 5: Create QuickSight Data Source

**Option A: Via AWS Console (Easiest)**

1. Go to: https://console.aws.amazon.com/quicksight
2. Click "Datasets" → "New Dataset"
3. Select "Athena"
4. Name: "DynamoDB Classifications"
5. Workgroup: "dynamodb-visualization"
6. Database: "recognitiondb"
7. Tables: "classifications"
8. Click "Create Dataset"

**Option B: Via AWS CLI**

```powershell
aws quicksight create-data-source `
    --aws-account-id 784055307907 `
    --data-source-id dynamodb-classifications-ds `
    --name "DynamoDB Classifications" `
    --type ATHENA `
    --data-source-parameters '{"AthenaParameters":{"WorkGroup":"dynamodb-visualization"}}' `
    --permissions '[{"Principal":"arn:aws:quicksight:us-east-1:784055307907:user/default/Vinay-AI","Actions":["quicksight:UpdateDataSourcePermissions","quicksight:DescribeDataSource","quicksight:DescribeDataSourcePermissions","quicksight:PassDataSource"]}]' `
    --region us-east-1
```

### Step 6: Create QuickSight Dataset

```powershell
# Get data source ARN
$dsArn = aws quicksight list-data-sources `
    --aws-account-id 784055307907 `
    --region us-east-1 `
    --query "DataSources[0].Arn" `
    --output text

# Create dataset
aws quicksight create-data-set `
    --aws-account-id 784055307907 `
    --data-set-id classifications-dataset `
    --name "Classifications Dataset" `
    --physical-table-map '{"classifications":{"RelationalTable":{"DataSourceArn":"'$dsArn'","Catalog":"AwsDataCatalog","Schema":"recognitiondb","Name":"classifications","InputColumns":[{"Name":"image","Type":"STRING"},{"Name":"labels","Type":"STRING"}]}}}' `
    --import-mode DIRECT_QUERY `
    --region us-east-1
```

### Step 7: Create QuickSight Analysis & Dashboard

```powershell
# Create analysis
aws quicksight create-analysis `
    --aws-account-id 784055307907 `
    --analysis-id classifications-analysis `
    --name "Image Classifications Analysis" `
    --source-entity '{"SourceTemplate":{"DataSetReferences":[{"DataSetPlaceholder":"classifications-dataset","DataSetArn":"arn:aws:quicksight:us-east-1:784055307907:dataset/classifications-dataset"}]}}' `
    --region us-east-1

# Create dashboard from analysis
aws quicksight create-dashboard `
    --aws-account-id 784055307907 `
    --dashboard-id classifications-dashboard `
    --name "Image Classifications Dashboard" `
    --source-entity '{"SourceAnalysis":{"Arn":"arn:aws:quicksight:us-east-1:784055307907:analysis/classifications-analysis","DataSetReferences":[{"DataSetPlaceholder":"classifications-dataset","DataSetArn":"arn:aws:quicksight:us-east-1:784055307907:dataset/classifications-dataset"}]}}' `
    --region us-east-1
```

---

## Common Issues & Fixes

### Issue 1: "Resource of type 'AWS::QuickSight::DataSource' with identifier 'dynamodb-athena-datasource' was not found"

**Cause:** QuickSight is not subscribed in the account

**Solution:**
```powershell
# Step 1: Subscribe to QuickSight (AWS Console)
# https://console.aws.amazon.com/quicksight

# Step 2: Re-deploy VisualizationStack
cdk deploy VisualizationStack --require-approval never --region us-east-1

# Step 3: Verify
aws quicksight describe-data-source `
    --aws-account-id 784055307907 `
    --data-source-id dynamodb-athena-datasource `
    --region us-east-1
```

### Issue 2: Athena Query Fails - "Access Denied" Writing to S3

**Cause:** Athena results bucket missing S3 bucket policy for Athena service

**Solution:**
```powershell
# Add Athena service principal to S3 bucket policy
aws s3api put-bucket-policy `
    --bucket athena-results-784055307907 `
    --policy '{
      "Version": "2012-10-17",
      "Statement": [
        {
          "Sid": "AllowAthenaService",
          "Effect": "Allow",
          "Principal": {"Service": "athena.amazonaws.com"},
          "Action": [
            "s3:GetObject",
            "s3:PutObject",
            "s3:AbortMultipartUpload",
            "s3:ListBucket",
            "s3:GetBucketLocation"
          ],
          "Resource": [
            "arn:aws:s3:::athena-results-784055307907",
            "arn:aws:s3:::athena-results-784055307907/*"
          ]
        }
      ]
    }' `
    --region us-east-1
```

### Issue 3: Glue Crawler Fails - "Cannot access table"

**Cause:** DynamoDB crawler role missing permissions

**Solution:**
```powershell
# Verify crawler role has DynamoDB permissions
$crawlerRole = aws glue get-crawler `
    --name dynamodb-classifications-crawler `
    --region us-east-1 `
    --query "Crawler.Role" `
    --output text

# Check role policies
aws iam list-attached-role-policies `
    --role-name $(Split-Path $crawlerRole -Leaf) `
    --region us-east-1

# Add DynamoDB full access if missing
aws iam attach-role-policy `
    --role-name "GlueCrawlerRole" `
    --policy-arn "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess" `
    --region us-east-1

# Retry crawler
aws glue start-crawler --name dynamodb-classifications-crawler --region us-east-1
```

### Issue 4: QuickSight Dataset Cannot Query

**Cause:** Lambda connector not executing properly

**Solution:**
```powershell
# Check Lambda function
aws lambda get-function-configuration `
    --function-name dynamodb `
    --region us-east-1 `
    --query "[Runtime,Timeout,MemorySize]"

# Increase timeout if needed
aws lambda update-function-configuration `
    --function-name dynamodb `
    --timeout 300 `
    --memory-size 1024 `
    --region us-east-1

# Check Lambda logs
aws logs tail /aws/lambda/dynamodb --follow --region us-east-1

# Retry dataset query in QuickSight Console
```

### Issue 5: "Insufficient Permissions" in QuickSight

**Cause:** QuickSight service role missing Athena permissions

**Solution:**
```powershell
# Get QuickSight service role
$qsRole = "aws-quicksight-service-role-v0"

# Attach required managed policies
aws iam attach-role-policy `
    --role-name $qsRole `
    --policy-arn "arn:aws:iam::aws:policy/service-role/AWSQuicksightAthenaAccess" `
    --region us-east-1

# Also attach custom inline policy
$policy = @{
    Version = "2012-10-17"
    Statement = @(
        @{
            Effect = "Allow"
            Action = @(
                "athena:GetQueryExecution",
                "athena:GetQueryResults",
                "athena:StartQueryExecution"
            )
            Resource = "*"
        },
        @{
            Effect = "Allow"
            Action = @(
                "s3:GetObject",
                "s3:ListBucket"
            )
            Resource = @(
                "arn:aws:s3:::athena-results-784055307907",
                "arn:aws:s3:::athena-results-784055307907/*"
            )
        }
    )
} | ConvertTo-Json

aws iam put-role-policy `
    --role-name $qsRole `
    --policy-name AthenaAccessPolicy `
    --policy-document $policy `
    --region us-east-1
```

### Issue 6: Spill Bucket Ownership Error

**Cause:** Athena connector cannot verify S3 bucket ownership

**Solution:**
```powershell
# Verify bucket ownership enforcement
aws s3api get-bucket-ownership-controls `
    --bucket athena-spill-* `
    --region us-east-1

# Set bucket ownership to BUCKET_OWNER_ENFORCED
aws s3api put-bucket-ownership-controls `
    --bucket "athena-spill-*" `
    --ownership-controls RuleDetailsList=[{ObjectOwnership=BucketOwnerEnforced}] `
    --region us-east-1

# Verify connector role has permission to check ownership
aws iam put-role-policy `
    --role-name ConnectorLambdaRole `
    --policy-name SpillBucketOwnershipCheck `
    --policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Action": "s3:GetBucketOwnershipControls",
        "Resource": "arn:aws:s3:::athena-spill-*"
      }]
    }' `
    --region us-east-1
```

---

## Advanced Configuration

### Custom Athena Query

```powershell
# Query with custom SQL
aws athena start-query-execution `
    --query-string "SELECT image, labels FROM recognitiondb.classifications WHERE labels LIKE '%Car%'" `
    --work-group dynamodb-visualization `
    --result-configuration OutputLocation=s3://athena-results-784055307907/results/ `
    --region us-east-1

# Get results
$queryId = "..." # from start-query-execution output
aws athena get-query-results --query-execution-id $queryId --region us-east-1
```

### Federated Query Configuration

```powershell
# Verify Athena data catalog points to connector
aws athena get-data-catalog --name recognitiondb --region us-east-1

# Create external schema pointing to DynamoDB
aws athena start-query-execution `
    --query-string "CREATE EXTERNAL TABLE IF NOT EXISTS recognitiondb.classifications USING EXTERNAL FUNCTION recognitiondb.dynamodb (image varchar, labels varchar) RETURNS varchar" `
    --work-group dynamodb-visualization `
    --region us-east-1
```

### Dashboard Template

Typical QuickSight dashboard should include:

1. **KPI Cards:**
   - Total images classified
   - Unique labels detected
   - Average confidence score

2. **Visualizations:**
   - Bar chart: Top labels by frequency
   - Table: Recent classifications
   - Pie chart: Label distribution

3. **Filters:**
   - By date range
   - By label
   - By confidence score

---

## Testing & Verification

### Test 1: Verify Glue Metadata

```powershell
# List Glue databases
aws glue get-databases --region us-east-1 --query "DatabaseList[*].Name"

# List tables in database
aws glue get-tables --database-name recognitiondb --region us-east-1 --query "TableList[*].Name"

# Get table schema
aws glue get-table `
    --database-name recognitiondb `
    --name classifications `
    --region us-east-1 `
    --query "Table.StorageDescriptor.Columns"
```

### Test 2: Query via Athena

```powershell
# Execute test query
$queryId = aws athena start-query-execution `
    --query-string "SELECT * FROM recognitiondb.classifications LIMIT 5" `
    --work-group dynamodb-visualization `
    --output text `
    --region us-east-1

# Wait for completion
Start-Sleep -Seconds 5

# Get results
aws athena get-query-results --query-execution-id $queryId --region us-east-1
```

### Test 3: Verify QuickSight Connectivity

```powershell
# Test data source connection
aws quicksight test-data-source-connection `
    --aws-account-id 784055307907 `
    --data-source-id dynamodb-athena-datasource `
    --region us-east-1
```

### Test 4: End-to-End Test

1. Upload images via API:
```powershell
python send_images.py
```

2. Wait for processing:
```powershell
Start-Sleep -Seconds 60
```

3. Verify DynamoDB:
```powershell
python scan_classifications.py --region us-east-1
```

4. Query via Athena:
```powershell
aws athena start-query-execution `
    --query-string "SELECT COUNT(*) FROM recognitiondb.classifications" `
    --work-group dynamodb-visualization `
    --region us-east-1
```

5. Check QuickSight:
- Log into: https://console.aws.amazon.com/quicksight
- Verify dataset is populated

---

## Troubleshooting Commands

### Diagnostic Commands

```powershell
# Check all QuickSight resources
aws quicksight list-data-sources --aws-account-id 784055307907 --region us-east-1
aws quicksight list-data-sets --aws-account-id 784055307907 --region us-east-1
aws quicksight list-analyses --aws-account-id 784055307907 --region us-east-1
aws quicksight list-dashboards --aws-account-id 784055307907 --region us-east-1

# Check Athena status
aws athena get-work-group --work-group dynamodb-visualization --region us-east-1
aws athena get-data-catalog --name recognitiondb --region us-east-1
aws athena list-query-executions --work-group dynamodb-visualization --region us-east-1

# Check Glue status
aws glue get-databases --region us-east-1
aws glue get-crawler --name dynamodb-classifications-crawler --region us-east-1
aws glue get-crawler-metrics --region us-east-1

# Check Lambda connector
aws lambda get-function --function-name dynamodb --region us-east-1
aws logs tail /aws/lambda/dynamodb --follow --region us-east-1

# Check S3 buckets
aws s3 ls s3://athena-results-784055307907/ --region us-east-1
aws s3 ls s3://athena-spill-*/ --region us-east-1

# Check IAM roles
aws iam get-role --role-name aws-quicksight-service-role-v0 --region us-east-1
aws iam list-attached-role-policies --role-name aws-quicksight-service-role-v0 --region us-east-1
```

### Log Analysis

```powershell
# Lambda connector logs
aws logs tail /aws/lambda/dynamodb --follow --region us-east-1 --since 30m

# Athena query logs
aws athena get-query-execution --query-execution-id <QUERY_ID> --region us-east-1

# Glue crawler logs
aws logs describe-log-groups --log-group-name-prefix "/aws-glue" --region us-east-1
```

### Manual Fixes

```powershell
# Restart Glue crawler
aws glue stop-crawler --name dynamodb-classifications-crawler --region us-east-1
Start-Sleep -Seconds 10
aws glue start-crawler --name dynamodb-classifications-crawler --region us-east-1

# Clear Athena cache
aws s3 rm s3://athena-results-784055307907/ --recursive --region us-east-1

# Re-create Lambda connector
aws lambda update-function-code `
    --function-name dynamodb `
    --s3-bucket <ASSET_BUCKET> `
    --s3-key dynamodb-connector.zip `
    --region us-east-1
```

---

## Support & Resources

### AWS Documentation
- [QuickSight Documentation](https://docs.aws.amazon.com/quicksight/)
- [Athena Federated Query](https://docs.aws.amazon.com/athena/latest/ug/querying-supported-statements.html)
- [Glue Data Catalog](https://docs.aws.amazon.com/glue/latest/dg/catalog-and-crawler.html)

### Key Concepts
- **Federated Query:** Query non-native data sources (like DynamoDB) using Athena
- **SAR (Serverless Application Repository):** Pre-built Lambda applications
- **Data Catalog:** Metadata repository for table schemas

### Useful Queries

```sql
-- Count images by label
SELECT label, COUNT(*) as count FROM recognitiondb.classifications
GROUP BY label ORDER BY count DESC LIMIT 10

-- Images with high confidence
SELECT image, confidence FROM recognitiondb.classifications
WHERE confidence > 90 LIMIT 20

-- Recent classifications
SELECT image, timestamp, labels FROM recognitiondb.classifications
ORDER BY timestamp DESC LIMIT 50
```

---

**Last Updated:** July 1, 2026  
**Account:** 784055307907  
**Region:** us-east-1  
**Version:** 1.0 - Complete Consolidated Guide
