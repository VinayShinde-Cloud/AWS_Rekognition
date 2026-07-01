# QuickSight Setup Guide - Cloudage Image Recognition

## Status: ✓ CONFIGURED

The QuickSight integration has been configured with the following components:

### Available Data Sources
1. **DynamoDB via Athena** (ID: `dynamodb-athena-datasource`) ← **USE THIS ONE**
2. DynbWithAthena (ID: `db825834-2b8a-45d9-8cb6-6e1567ebe93e`)
3. DYNAMODB (ID: `015c985f-6e75-4993-ba15-4dadb93109b1`)

### User Permissions
- **QuickSight User:** Vinay-AI
- **Account:** 784055307907
- **Region:** us-east-1
- **Namespace:** default

### Backend Infrastructure
- **Athena Workgroup:** `dynamodb-visualization`
- **Athena Catalog:** `recognitiondb` (Federated DynamoDB connector)
- **Glue Database:** `recognitiondb`
- **Glue Crawler:** `dynamodb-classifications-crawler`
- **DynamoDB Table:** `RekognitionStack-Classifications0C921F6C-1VMPN4XOM4W5A`
  - **Partition Key:** image (string)
  - **Data:** image filenames and detected labels from AWS Rekognition

## How to Access

### Step 1: Log into QuickSight
1. Go to: https://us-east-1.quicksight.aws.amazon.com
2. Log in as: **Vinay-AI**
3. Use your AWS credentials

### Step 2: Create a Dataset
1. Click **Datasets** in the left menu
2. Click **Create Dataset** (new dataset button)
3. Select **DynamoDB via Athena** data source
4. Under **Databases**, select: **recognitiondb**
5. Under **Tables**, select: **classifications**
6. Click **Create Dataset**

### Step 3: Create a Visualization
1. Click **Create Analysis** (or click the dataset)
2. Drag fields to visualize:
   - **Rows:** image (to list all images)
   - **Values:** labels (to show detected labels)
   - **Filters:** image or labels (to search)
3. Create visualizations to explore:
   - Bar chart: Labels by frequency
   - Table: All images and their detected labels
   - Tree map: Label hierarchy

## Troubleshooting

### Issue: No data showing in QuickSight

**Solution 1: Ensure Glue Crawler has Run**
```bash
# Check crawler status
aws glue get-crawler --name dynamodb-classifications-crawler --region us-east-1

# If status is READY (not RUNNING), start it
aws glue start-crawler --name dynamodb-classifications-crawler --region us-east-1

# Wait 2-3 minutes for crawler to complete
```

**Solution 2: Verify DynamoDB has Data**
```bash
# Check if classifications are in DynamoDB
cd solution-files/python
python check_dynamo.py

# If empty, send test images
python send_images.py --count 5
```

**Solution 3: Verify QuickSight Permissions**
```bash
# Check data source permissions
aws quicksight describe-data-source-permissions \
  --aws-account-id 784055307907 \
  --data-source-id dynamodb-athena-datasource \
  --region us-east-1
```

**Solution 4: Verify Athena Workgroup**
```bash
# Check workgroup status
aws athena get-work-group --work-group dynamodb-visualization --region us-east-1
```

## Architecture Flow

```
DynamoDB Classifications Table
    (5 images with detected labels)
           |
           v
Glue Crawler (discovers schema)
           |
           v
Glue Data Catalog (recognitiondb.classifications)
           |
           v
Athena DynamoDB Connector (federated query engine)
           |
           v
Athena Workgroup (executes SQL queries)
           |
           v
QuickSight Data Source (connects to Athena)
           |
           v
Datasets → Visualizations → Insights
```

## Sample Queries

Once connected, you can run SQL queries on the DynamoDB data:

```sql
-- View all images and their labels
SELECT image, labels 
FROM recognitiondb.classifications

-- Count labels by frequency
SELECT * FROM recognitiondb.classifications
WHERE image LIKE 'car%'

-- View specific vehicles
SELECT image, labels 
FROM recognitiondb.classifications
WHERE labels LIKE '%Car%'
```

## Next Steps

1. ✓ Ensure DynamoDB has classification data (run `python send_images.py` if needed)
2. ✓ Run Glue Crawler to populate schema
3. ✓ Create QuickSight Dataset (see Step 2 above)
4. ✓ Create visualizations to explore insights
5. ✓ Build dashboards for operations team

## Support

If you encounter issues:
1. Check CloudWatch Logs for Athena connector Lambda
2. Verify IAM permissions on `aws-quicksight-service-role-v0`
3. Ensure Glue crawler has run recently
4. Confirm DynamoDB table has data using `scan_classifications.py`

---
**Last Updated:** June 4, 2026
**Status:** Ready for use
