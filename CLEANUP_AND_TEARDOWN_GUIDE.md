# Cloudage Image Rekognition - Cleanup & Teardown Guide

## Overview

This guide explains how to safely clean up and completely remove all AWS resources created during the deployment of the Cloudage Image Rekognition pipeline.

**⚠️ WARNING:** Cleanup operations are **DESTRUCTIVE AND IRREVERSIBLE**. Before proceeding:
- ✅ Verify you no longer need any data
- ✅ Have backups of important data
- ✅ Confirm this is the correct AWS account
- ✅ Understand billing implications

---

## Quick Cleanup Commands

### Option 1: Automated Cleanup Script (RECOMMENDED)

#### Preview What Will Be Deleted (No Risk)
```powershell
cd solution-files\python
.venv\Scripts\Activate.ps1
.\cleanup-teardown.ps1 -DryRun
```

**Output shows everything that would be deleted without actually deleting anything.**

#### Perform Cleanup (With Confirmation)
```powershell
.\cleanup-teardown.ps1
```

**Prompts for confirmation before deleting. Type `DELETE EVERYTHING` to confirm.**

#### Cleanup Without Prompts (Use with Caution!)
```powershell
.\cleanup-teardown.ps1 -SkipPrompt
```

**Deletes everything immediately without confirmation. Only use if sure!**

#### Get Help
```powershell
.\cleanup-teardown.ps1 -Help
```

---

## What Gets Deleted

### Phase 1: CloudFormation Stacks (in reverse order)

| Stack | Resources | Time |
|-------|-----------|------|
| **VisualizationStack** | Athena, Glue, Lambda connector, QuickSight, S3 | 5 min |
| **RekognitionStack** | DynamoDB, Lambda functions, API Gateway | 5 min |
| **IntegrationStack** | SNS, SQS, Lambda, API Gateway, S3 | 5 min |
| **APIStack** | API Gateway, Lambda, S3, SNS, SQS | 5 min |
| **Total** | | ~20 min |

### Phase 2: Orphaned Resources (RemovalPolicy.RETAIN)

Even though CDK destroys the stacks, some resources are configured to remain:

**S3 Buckets (deleted with all objects):**
- `athena-results-784055307907` (query results)
- `athena-spill-*` (Athena temporary storage)
- `sagemaker-us-east-1-784055307907` (images - **DATA LOSS**)

**DynamoDB Tables (deleted with all data):**
- `RekognitionStack-Classifications*` (all classifications - **DATA LOSS**)

**Athena Resources:**
- `dynamodb-visualization` (workgroup)

**Glue Resources:**
- `recognitiondb` (database)
- `dynamodb-classifications-crawler` (crawler)

**QuickSight Resources:**
- `dynamodb-athena-datasource` (data source)

### Phase 3: Additional Resources

**IAM Roles & Policies:**
- ImageRecognitionRole
- ListImagesLambdaRole
- GlueCrawlerRole
- ConnectorLambdaRole
- And attached policies

**Lambda Functions:**
- ImageGetAndSaveLambda
- image_recognition
- ListImagesLambda
- send_email
- SaveXMLLambda
- Athena DynamoDB Connector

**Event Sources:**
- Lambda event source mappings
- S3 event notifications
- SNS subscriptions

**Other Services:**
- CloudWatch log groups (`/aws/lambda/*`)
- API Gateway endpoints
- Lambda layers
- IAM roles and policies

---

## Step-by-Step Cleanup Procedure

### Step 1: Backup Important Data (Optional)

If you need to preserve any data before cleanup:

```powershell
# Export DynamoDB table
aws dynamodb scan `
    --table-name RekognitionStack-Classifications0C921F6C-V6CZOJO8NE0J `
    --output json `
    --region us-east-1 `
    | Out-File dynamodb-backup.json

# Download all images from S3
aws s3 sync s3://sagemaker-us-east-1-784055307907 ./backup-images --region us-east-1

# Export Glue metadata
aws glue get-tables --database-name recognitiondb --region us-east-1 > glue-metadata.json
```

### Step 2: Preview Cleanup (Dry Run)

Always preview before deleting:

```powershell
cd solution-files\python
.venv\Scripts\Activate.ps1
.\cleanup-teardown.ps1 -DryRun
```

**Review the output to verify it matches your expectations.**

### Step 3: Perform Cleanup

Run the cleanup script:

```powershell
.\cleanup-teardown.ps1
```

**Follow the prompts and type `DELETE EVERYTHING` to confirm.**

### Step 4: Verify Cleanup

Confirm all resources have been deleted:

```powershell
# Check CloudFormation stacks
aws cloudformation list-stacks --region us-east-1 `
    --query "StackSummaries[?StackStatus=='CREATE_COMPLETE'].StackName"

# Check S3 buckets
aws s3 ls --region us-east-1

# Check Lambda functions
aws lambda list-functions --region us-east-1 --query "Functions[*].FunctionName"

# Check DynamoDB tables
aws dynamodb list-tables --region us-east-1

# Check SNS topics
aws sns list-topics --region us-east-1

# Check SQS queues
aws sqs list-queues --region us-east-1
```

**All lists should be empty (except AWS-managed resources).**

---

## Manual Cleanup (If Automated Script Fails)

### Destroy Stacks Manually

```powershell
# Destroy in reverse order
cdk destroy VisualizationStack --force --region us-east-1
cdk destroy RekognitionStack --force --region us-east-1
cdk destroy IntegrationStack --force --region us-east-1
cdk destroy APIStack --force --region us-east-1
```

### Delete S3 Buckets Manually

```powershell
# List buckets matching pattern
aws s3 ls --region us-east-1 | grep -E "(athena|sagemaker)"

# Remove all objects from bucket
aws s3 rm s3://athena-results-784055307907 --recursive --region us-east-1
aws s3 rm s3://sagemaker-us-east-1-784055307907 --recursive --region us-east-1

# Delete empty bucket
aws s3api delete-bucket --bucket athena-results-784055307907 --region us-east-1
aws s3api delete-bucket --bucket sagemaker-us-east-1-784055307907 --region us-east-1
```

### Delete DynamoDB Tables Manually

```powershell
# List tables
aws dynamodb list-tables --region us-east-1

# Delete specific table
aws dynamodb delete-table --table-name RekognitionStack-Classifications0C921F6C-V6CZOJO8NE0J --region us-east-1
```

### Delete Athena Resources Manually

```powershell
# Delete workgroup
aws athena delete-work-group --work-group dynamodb-visualization --region us-east-1

# Delete data catalog
aws athena delete-data-catalog --name recognitiondb --region us-east-1
```

### Delete Glue Resources Manually

```powershell
# Delete crawler
aws glue delete-crawler --name dynamodb-classifications-crawler --region us-east-1

# Delete database
aws glue delete-database --catalog-id 784055307907 --name recognitiondb --region us-east-1

# List and delete tables manually if needed
aws glue get-tables --database-name recognitiondb --region us-east-1
```

### Delete QuickSight Resources Manually

```powershell
# List data sources
aws quicksight list-data-sources --aws-account-id 784055307907 --region us-east-1

# Delete data source
aws quicksight delete-data-source `
    --aws-account-id 784055307907 `
    --data-source-id dynamodb-athena-datasource `
    --region us-east-1
```

### Delete CloudWatch Log Groups Manually

```powershell
# List log groups
aws logs describe-log-groups --region us-east-1

# Delete log groups for Lambda
aws logs delete-log-group --log-group-name /aws/lambda/image_recognition --region us-east-1
aws logs delete-log-group --log-group-name /aws/lambda/ImageGetAndSaveLambda --region us-east-1
aws logs delete-log-group --log-group-name /aws/lambda/ListImagesLambda --region us-east-1
aws logs delete-log-group --log-group-name /aws/lambda/send_email --region us-east-1
aws logs delete-log-group --log-group-name /aws/lambda/SaveXMLLambda --region us-east-1
```

---

## Partial Cleanup

### Delete Only Specific Stack

If you want to keep some stacks and only delete specific ones:

```powershell
# Using CDK
cdk destroy APIStack --force --region us-east-1

# This will delete only APIStack and its resources
# Other stacks remain intact
```

**Caution:** Deleting intermediate stacks may break dependencies for higher stacks.

### Delete Only Data (Keep Infrastructure)

To keep the infrastructure but delete all data:

```powershell
# Clear DynamoDB table (keep table structure)
aws dynamodb scan --table-name RekognitionStack-Classifications0C921F6C-V6CZOJO8NE0J `
    --region us-east-1 `
    --projection-expression "image" `
    --query "Items[*].image.S" `
    | ConvertFrom-Json `
    | ForEach-Object { 
        aws dynamodb delete-item `
            --table-name RekognitionStack-Classifications0C921F6C-V6CZOJO8NE0J `
            --key "{\"image\":{\"S\":\"$_\"}}" `
            --region us-east-1
    }

# Clear S3 bucket (keep bucket)
aws s3 rm s3://sagemaker-us-east-1-784055307907 --recursive --region us-east-1

# Delete Athena query results
aws s3 rm s3://athena-results-784055307907 --recursive --region us-east-1
```

---

## Troubleshooting Cleanup Issues

### Issue: "Resource in use" Error

**Symptom:** Stack deletion fails with "Resource is in use"

**Solution:**
```powershell
# Check what's using the resource
aws cloudformation describe-stack-resources --stack-name APIStack --region us-east-1

# Wait a few minutes and retry
Start-Sleep -Seconds 60
.\cleanup-teardown.ps1

# Or manually delete dependent resources first
```

### Issue: S3 Bucket Not Empty

**Symptom:** "Bucket is not empty" error

**Solution:**
```powershell
# Remove all versioned objects
aws s3api list-object-versions --bucket athena-results-784055307907 --region us-east-1 `
    --query "Versions[].{Key:Key, VersionId:VersionId}" `
    | ConvertFrom-Json `
    | ForEach-Object {
        aws s3api delete-object `
            --bucket athena-results-784055307907 `
            --key $_.Key `
            --version-id $_.VersionId `
            --region us-east-1
    }

# Delete delete markers
aws s3api list-object-versions --bucket athena-results-784055307907 --region us-east-1 `
    --query "DeleteMarkers[].{Key:Key, VersionId:VersionId}" `
    | ConvertFrom-Json `
    | ForEach-Object {
        aws s3api delete-object `
            --bucket athena-results-784055307907 `
            --key $_.Key `
            --version-id $_.VersionId `
            --region us-east-1
    }

# Now try to delete bucket
aws s3api delete-bucket --bucket athena-results-784055307907 --region us-east-1
```

### Issue: Lambda Still Executing

**Symptom:** Can't delete Lambda because it's still processing

**Solution:**
```powershell
# Wait for in-flight executions to complete
Start-Sleep -Seconds 30

# Check if there are messages in queues
aws sqs get-queue-attributes `
    --queue-url "https://sqs.us-east-1.amazonaws.com/784055307907/APIStack-uploadedimagequeue43D6CD3D-nkTU7aynvOOf" `
    --attribute-names ApproximateNumberOfMessages `
    --region us-east-1

# Purge the queues
aws sqs purge-queue `
    --queue-url "https://sqs.us-east-1.amazonaws.com/784055307907/APIStack-uploadedimagequeue43D6CD3D-nkTU7aynvOOf" `
    --region us-east-1

# Retry cleanup
.\cleanup-teardown.ps1
```

### Issue: DynamoDB Table in Use

**Symptom:** "Cannot delete table that is being used"

**Solution:**
```powershell
# Check for ongoing operations
aws dynamodb describe-table `
    --table-name RekognitionStack-Classifications0C921F6C-V6CZOJO8NE0J `
    --region us-east-1 `
    --query "Table.[TableStatus,RestoreSummary]"

# Wait and retry
Start-Sleep -Seconds 30
.\cleanup-teardown.ps1
```

---

## Cleanup Verification Checklist

After cleanup, verify all resources are deleted:

```powershell
# ✓ No CloudFormation stacks
aws cloudformation list-stacks --region us-east-1 `
    --query "StackSummaries[?StackStatus!='DELETE_COMPLETE'].StackName"

# ✓ No Lambda functions
aws lambda list-functions --region us-east-1 --query "Functions[*].FunctionName"

# ✓ No DynamoDB tables
aws dynamodb list-tables --region us-east-1 --query "TableNames"

# ✓ No SNS topics (except AWS defaults)
aws sns list-topics --region us-east-1 --query "Topics[*].TopicArn" | grep -v aws:

# ✓ No SQS queues
aws sqs list-queues --region us-east-1 --query "QueueUrls"

# ✓ No S3 buckets (except for other projects)
aws s3 ls --region us-east-1 | grep -E "(athena|sagemaker)"

# ✓ No Athena workgroups
aws athena list-work-groups --region us-east-1 --query "WorkGroups[*].Name"

# ✓ No Glue databases
aws glue get-databases --region us-east-1 --query "DatabaseList[*].Name"

# ✓ No QuickSight data sources
aws quicksight list-data-sources --aws-account-id 784055307907 --region us-east-1 `
    --query "DataSources[*].DataSourceId"
```

**All commands should return empty results (except AWS-managed resources).**

---

## Cost Implications of Cleanup

After cleanup:
- **No charges** for deleted resources
- **Storage charges** stop immediately for S3 buckets
- **On-demand DynamoDB** charges stop immediately
- **Lambda invocations** no longer charged
- **Athena queries** no longer charged
- **Glue crawler** no longer charged

**CloudFormation stack deletion may take 20-30 minutes.**

---

## Recovery After Cleanup

### Can I Recover Deleted Data?

**No.** Cleanup is permanent and cannot be undone for:
- DynamoDB table data
- S3 bucket contents
- Glue table schemas

### Can I Re-Deploy After Cleanup?

**Yes.** After cleanup is complete, you can re-deploy:

```powershell
cd solution-files\python
.venv\Scripts\Activate.ps1
.\deploy-manual.ps1
```

**The deployment will create a fresh instance of all resources.**

### Partial Re-Deploy

If you accidentally delete something, you can re-deploy just that stack:

```powershell
.\deploy-manual.ps1 -Stack RekognitionStack
```

---

## Backup Before Cleanup (Recommended)

### Export Data to Files

```powershell
# Export DynamoDB data
aws dynamodb scan `
    --table-name RekognitionStack-Classifications0C921F6C-V6CZOJO8NE0J `
    --output json `
    --region us-east-1 `
    | Out-File classifications-backup-$(Get-Date -Format yyyy-MM-dd-HHmm).json

# List all images in S3
aws s3 ls s3://sagemaker-us-east-1-784055307907 --recursive `
    | Out-File s3-inventory-$(Get-Date -Format yyyy-MM-dd-HHmm).txt

# Export Glue schema
aws glue get-tables --database-name recognitiondb --region us-east-1 `
    | Out-File glue-schema-$(Get-Date -Format yyyy-MM-dd-HHmm).json

# Download all images
aws s3 sync s3://sagemaker-us-east-1-784055307907 "./backup-images-$(Get-Date -Format yyyy-MM-dd-HHmm)" --region us-east-1
```

### Store Backups Safely

Move backups to secure location:
- External hard drive
- Cloud storage (AWS S3 in another account)
- Local network backup

---

## Support

For cleanup issues:
1. Check the Troubleshooting section above
2. Review CloudFormation events: `aws cloudformation describe-stack-events --stack-name <StackName>`
3. Check AWS Console for resource status
4. Contact AWS support if manual cleanup needed

---

**Last Updated:** July 1, 2026  
**Account:** 784055307907  
**Region:** us-east-1  

⚠️ **WARNING:** This operation is destructive and irreversible. Ensure you have backups before proceeding.
