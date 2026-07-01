# QuickSight Import Error Fix

## Error Fixed: "User does not have permission to access the above project"

### Root Cause
The QuickSight user `Vinay-AI` lacked sufficient permissions to:
1. Access the Athena data source
2. Query the DynamoDB table through Athena
3. Access Glue Data Catalog
4. Use the Athena workgroup

### Solution Applied

#### 1. Data Source Permissions ✓
Granted `Vinay-AI` the following permissions on `dynamodb-athena-datasource`:
- `quicksight:DescribeDataSource`
- `quicksight:DescribeDataSourcePermissions`
- `quicksight:PassDataSource`
- `quicksight:UpdateDataSource`
- `quicksight:DeleteDataSource`
- `quicksight:UpdateDataSourcePermissions`

#### 2. Service Role Permissions ✓
Ensured `aws-quicksight-service-role-v0` has:
- `AWSQuicksightAthenaAccess` (AWS managed policy)
- Inline policy for DynamoDB read access
- Inline policy for Glue Catalog access
- Inline policy for S3 (Athena results bucket) access

#### 3. User Role Configuration ✓
Set `Vinay-AI` QuickSight user role to `AUTHOR`:
- Can create and edit datasets
- Can create analyses and visualizations
- Can access data sources

### Now Try Again

1. **Go to QuickSight Console**
   ```
   https://us-east-1.quicksight.aws.amazon.com
   ```

2. **Create New Dataset**
   - Click **Datasets** → **Create Dataset**
   - Select **DynamoDB via Athena** data source
   - Click **Create New Table**

3. **Import Data**
   - Database: `recognitiondb`
   - Table: `classifications`
   - Click **Select**
   - Click **Visualize** to import

4. **Create Visualizations**
   - Drag `image` field to **Rows**
   - Drag `labels` field to **Values**
   - Create filters, charts, and dashboards

## Troubleshooting If Still Getting Error

### Check 1: Verify Glue Table Exists
```bash
aws glue get-tables \
    --database-name recognitiondb \
    --region us-east-1 \
    --query "TableList[*].Name"
```
**Expected output:** `["classifications"]`

**If empty:** Run the Glue crawler:
```bash
aws glue start-crawler \
    --name dynamodb-classifications-crawler \
    --region us-east-1

# Wait 2-3 minutes, then check crawler status:
aws glue get-crawler \
    --name dynamodb-classifications-crawler \
    --region us-east-1 \
    --query "Crawler.State"
```

### Check 2: Verify DynamoDB Has Data
```bash
cd solution-files/python
python check_dynamo.py
```
**Expected output:** 5+ images with detected labels

**If empty:** Send test images:
```bash
python send_images.py --count 5
```

### Check 3: Verify Athena Workgroup
```bash
aws athena get-work-group \
    --work-group dynamodb-visualization \
    --region us-east-1 \
    --query "WorkGroup.State"
```
**Expected output:** `"ENABLED"`

### Check 4: Test Athena Query Directly
```bash
aws athena start-query-execution \
    --query-string "SELECT * FROM recognitiondb.classifications LIMIT 5" \
    --query-execution-context Database=recognitiondb \
    --result-configuration OutputLocation=s3://athena-results-784055307907/results/ \
    --work-group dynamodb-visualization \
    --region us-east-1
```

### Check 5: Verify QuickSight Data Source Connection
```bash
aws quicksight describe-data-source \
    --aws-account-id 784055307907 \
    --data-source-id dynamodb-athena-datasource \
    --region us-east-1
```

### Check 6: Verify User Permissions
```bash
aws quicksight describe-user \
    --aws-account-id 784055307907 \
    --user-name Vinay-AI \
    --namespace default \
    --region us-east-1
```
**Expected:** User role should be `AUTHOR`

### Check 7: Verify Service Role Permissions
```bash
aws iam list-attached-role-policies \
    --role-name aws-quicksight-service-role-v0 \
    --query "AttachedPolicies[*].PolicyName"
```
**Expected to include:** `AWSQuicksightAthenaAccess`

## Common Issues and Solutions

### Issue: "Table not found in Glue"
**Solution:** Run Glue crawler (see Check 1 above)

### Issue: "Cannot connect to Athena"
**Solution:** Verify workgroup exists and is enabled (see Check 3 above)

### Issue: "S3 access denied"
**Solution:** Ensure S3 bucket policy allows QuickSight:
```bash
aws s3api get-bucket-policy \
    --bucket athena-results-784055307907 \
    --region us-east-1
```

### Issue: "DynamoDB access denied"
**Solution:** The inline policy has been added. If still failing:
```bash
aws iam list-role-policies \
    --role-name aws-quicksight-service-role-v0
```
Should include: `QuickSightAthenaAndDynamoDBAccess`

## Manual Permission Fix (If Needed)

If the automated script didn't fully work, manually apply these permissions:

### Update Data Source Permissions
```bash
aws quicksight update-data-source-permissions \
    --aws-account-id 784055307907 \
    --data-source-id dynamodb-athena-datasource \
    --grant-permissions \
        Principal=arn:aws:quicksight:us-east-1:784055307907:user/default/Vinay-AI,\
        Actions=quicksight:DescribeDataSource,\
        quicksight:DescribeDataSourcePermissions,\
        quicksight:PassDataSource,\
        quicksight:UpdateDataSource \
    --region us-east-1
```

### Attach Athena Policy to Service Role
```bash
aws iam attach-role-policy \
    --role-name aws-quicksight-service-role-v0 \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSQuicksightAthenaAccess
```

### Update User Role to AUTHOR
```bash
aws quicksight update-user \
    --aws-account-id 784055307907 \
    --user-name Vinay-AI \
    --namespace default \
    --role AUTHOR \
    --region us-east-1
```

## Next Steps After Import Success

1. **Create Dataset**
   - Select all columns from `classifications` table
   - Click **Create Dataset**

2. **Explore Data**
   - Open dataset in analysis mode
   - Drag `image` to Rows
   - Drag `labels` to Values
   - Create bar charts of labels by frequency

3. **Build Dashboard**
   - Add visualizations to shared dashboard
   - Share with team members
   - Use filters for navigation

4. **Set Up Alerts** (Optional)
   - Create anomaly detection on label distributions
   - Set up scheduled refreshes
   - Monitor for unusual vehicle types

## Reference URLs

- **QuickSight Console:** https://us-east-1.quicksight.aws.amazon.com
- **AWS IAM Console:** https://console.aws.amazon.com/iam/
- **AWS Athena:** https://console.aws.amazon.com/athena/
- **AWS Glue:** https://console.aws.amazon.com/glue/
- **AWS DynamoDB:** https://console.aws.amazon.com/dynamodb/

---
**Issue Resolved:** June 4, 2026
**Permissions Applied:** All required access levels
**Status:** Ready for import
