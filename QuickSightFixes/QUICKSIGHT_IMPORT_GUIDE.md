# QuickSight Import Guide - Step by Step

## Overview

Your Cloudage image recognition system is now ready to use QuickSight for visualization. This guide walks you through importing DynamoDB data via Athena and creating visualizations.

**Status:** ✓ All systems operational
- 25+ images classified with vehicle labels
- DynamoDB populated and queryable
- Glue Data Catalog configured
- Athena working with DynamoDB Connector
- Service role has all required permissions

---

## Step 1: Open QuickSight Console

Navigate to:
```
https://us-east-1.quicksight.aws.amazon.com
```

Your user `Vinay-AI` should already have ADMIN access.

---

## Step 2: Create a New Dataset

### 2a. Go to Datasets
- Click **Datasets** in the left sidebar
- You'll see any existing datasets

### 2b. Create New Dataset
- Click **Create Dataset** (blue button, top right)
- You'll see a list of available data sources

---

## Step 3: Select DynamoDB via Athena Data Source

### 3a. Look for Available Data Sources
You should see three data sources:
- `DYNAMODB` (ATHENA)
- `DynbWithAthena` (ATHENA)
- **`DynamoDB via Athena`** ← **Select this one**

Click on **"DynamoDB via Athena"**

### 3b. Create New Table
- Click **Create New Table** (or "Create new Dataset from this source")
- You'll see a form to select database and table

---

## Step 4: Select Database and Table

### 4a. Choose Database
- **Database dropdown:** Select `recognitiondb`

### 4b. Choose Table
- **Table dropdown:** Select the classifications table
  - Name will be something like: `rekognitionstack_classifications0c921f6c_1vmpn4xom4w5a`
  - This table contains all 25+ classified images

### 4c. Confirm Selection
- Click **Select** or **Next**
- QuickSight will query the table structure

---

## Step 5: Visualize the Data

### 5a. Create or Visualize
- Click **Visualize** (or **Create Analysis** depending on QuickSight version)
- Wait 3-5 seconds for the query to execute
- You should see the dataset loaded with all columns

### 5b. Your Data Columns
The dataset will have these columns:
- `image` — Image filename (car-001.jpg, truck-002.jpg, etc.)
- `labels` — Array of detected labels from Rekognition
- `confidence` — Confidence scores (optional)
- `timestamp` — When the image was processed

---

## Step 6: Create Your First Visualization

### 6a. Build a Bar Chart (Label Frequency)

1. **Open the dataset** if not already open
2. **Create a new visual:**
   - Click **+ Add** (to add a visualization)
   - Or look for **Create visualization** option

3. **Configure visualization:**
   - **Chart type:** Bar chart
   - **X-axis (Rows):** Drag `image` field
   - **Y-axis (Values):** Add a count aggregation
   - **Color:** Optional — drag `labels` for more dimensions

4. **View results:**
   - You'll see a bar chart showing which images have the most labels detected

### 6b. Create a Table View

1. **Alternative:** Use the **Table** visual to see raw data
   - Drag `image` to Rows
   - Drag `labels` to Values
   - See all classifications in tabular format

### 6c. Add Filters

1. **Filter by vehicle type:**
   - Click **Filter** in the toolbar
   - Add a filter on `image` (filter by car-*, truck-*, etc.)
   - See only those classifications

---

## Step 7: Save and Share

### 7a. Save the Analysis
- Click **Save** (top left)
- Give it a name like "Vehicle Classification Dashboard"
- Click **Save**

### 7b. Create a Dashboard
- From the saved analysis, click **Share** → **Publish dashboard**
- Or create a new dashboard and add visualizations to it

### 7c. Share with Team
- Click **Share** → **Invite users**
- Give other team members access

---

## Common Visualizations to Create

### 1. Label Frequency Chart
Shows which labels appear most often across all images.

```
Setup:
  - Rows: labels (as dimension)
  - Values: COUNT (aggregate)
  - Sort: Descending
```

**Expected top labels:**
- Car, Vehicle, Transportation
- Machine, Wheel
- Sedan, Truck, Bus

### 2. Image Classification Table
Shows all images with their detected labels.

```
Setup:
  - Rows: image
  - Values: labels (as multi-value field)
  - Filter: [optional] by image name pattern
```

### 3. Vehicle Type Distribution
Shows breakdown by vehicle category (cars vs trucks vs buses).

```
Setup:
  - Rows: image (with filter prefix like 'car-*', 'truck-*')
  - Values: COUNT
  - Filter: image contains specific vehicle type
```

### 4. Label Co-occurrence Matrix
Shows which labels typically appear together.

```
Setup:
  - Rows: image
  - Columns: labels
  - Values: COUNT
```

---

## Troubleshooting

### Issue: "No data in the table"
- Check DynamoDB has images: `python check_dynamo.py`
- If empty, send images: `python send_images.py --count 5`

### Issue: "Cannot find table in database"
- Glue crawler might not have run
- Start crawler: `aws glue start-crawler --name dynamodb-classifications-crawler --region us-east-1`
- Wait 2-3 minutes for completion

### Issue: "Error connecting to data source"
- Service role missing DynamoDB permissions
- Run: `python quicksight_fix.py`
- Wait 5-10 minutes for IAM policy propagation
- Refresh QuickSight console

### Issue: "Query timeout"
- Athena connector is still initializing
- Try again in 30 seconds
- Large dataset (100+ images) might take longer

### Issue: Dataset shows 0 rows but DynamoDB has data
- **Wait for Glue crawler to finish**
  - It needs to discover the table schema
  - Check status: `aws glue get-crawler --name dynamodb-classifications-crawler --region us-east-1 --query "Crawler.State"`
  - Should be `READY` or `STOPPING`

---

## Quick Reference

| Task | Command |
|------|---------|
| Check data in DynamoDB | `python check_dynamo.py` |
| Send more images | `python send_images.py --count 10` |
| Verify Glue crawler ran | `aws glue get-crawler --name dynamodb-classifications-crawler --region us-east-1 --query "Crawler.LastCrawl.Status"` |
| Check Athena workgroup | `aws athena get-work-group --work-group dynamodb-visualization --region us-east-1 --query "WorkGroup.State"` |
| Fix QuickSight permissions | `python quicksight_fix.py` |
| Verify service role policy | `aws iam get-role-policy --role-name aws-quicksight-service-role-v0 --policy-name QuickSightDynamoDBAccess` |

---

## API References

QuickSight Console:
- **Home:** https://console.aws.amazon.com/quicksight/
- **Datasets:** https://us-east-1.quicksight.aws.amazon.com/sn/datasets
- **Analyses:** https://us-east-1.quicksight.aws.amazon.com/sn/analyses
- **Dashboards:** https://us-east-1.quicksight.aws.amazon.com/sn/dashboards

Related AWS Services:
- **Athena Queries:** https://console.aws.amazon.com/athena/
- **DynamoDB Tables:** https://console.aws.amazon.com/dynamodb/
- **Glue Catalog:** https://console.aws.amazon.com/glue/

---

## Next Steps After Import Success

1. **Explore the data**
   - Create visualizations with different dimensions
   - Apply filters for specific vehicle types

2. **Add more data**
   - Run `send_images.py` with more images
   - See how visualizations update

3. **Share dashboards**
   - Create a public dashboard
   - Send the link to team members

4. **Set up alerts** (Optional)
   - Create anomaly detection on label distributions
   - Set up scheduled refreshes

---

## Still Need Help?

Run the diagnostic script to verify everything is working:
```bash
python diagnose_quicksight.py
```

This will check:
- ✓ QuickSight user permissions
- ✓ Data source configuration
- ✓ Service role policies
- ✓ Glue database and tables
- ✓ DynamoDB data
- ✓ Athena workgroup
- ✓ S3 access

**All checks should pass before creating datasets.**

---

**Happy visualizing!**

For more information, see:
- `QUICKSIGHT_READY.md` — Status and technical details
- `DEPLOYMENT_COMPLETE.md` — Full system documentation
- `QUICKSTART.md` — Quick reference guide
