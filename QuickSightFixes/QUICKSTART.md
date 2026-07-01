# Cloudage QuickStart - 5 Minute Setup

## 1️⃣ View Data in QuickSight (2 minutes)

```bash
# Open this URL in your browser:
# https://us-east-1.quicksight.aws.amazon.com

# Log in as:
Username: Vinay-AI
Password: (your AWS credentials)
```

## 2️⃣ Create Dataset (2 minutes)

1. Click **Datasets** (left menu)
2. Click **Create Dataset** (top right)
3. Select **DynamoDB via Athena**
4. In dialog, choose:
   - Database: `recognitiondb`
   - Table: `classifications`
5. Click **Select** → **Visualize**

## 3️⃣ Create Your First Visualization (1 minute)

1. Drag **image** field to **Rows**
2. Drag **labels** field to **Values**
3. See all 5 images with their detected vehicle labels
4. Create charts, filters, and dashboards

## Done! 🎉

You now have live vehicle classification data visualized in QuickSight.

---

## Useful Commands

### Send More Test Images
```bash
cd solution-files/python
python send_images.py --count 5
```

### Check What Data is Stored
```bash
cd solution-files/python
python check_dynamo.py
```

### View Live Lambda Logs
```bash
aws logs tail /aws/lambda/image_recognition --follow --region us-east-1
```

### Test API Endpoint
```bash
curl "https://gy164f9l9d.execute-api.us-east-1.amazonaws.com/prod/?url=https://images.pexels.com/photos/1007410/pexels-photo-1007410.jpeg&name=test.jpg"
```

---

## Troubleshooting

### "User does not have permission" Error
→ See: `QUICKSIGHT_IMPORT_FIX.md`

### No data showing in QuickSight
→ See: `QUICKSIGHT_SETUP.md` → "Troubleshooting"

### Images not in DynamoDB
→ Check: `python check_dynamo.py`

---

## Architecture at a Glance

```
Your Image URL
     ↓
API Gateway
     ↓
Lambda downloads + S3 upload
     ↓
S3 triggers SNS → SQS
     ↓
Lambda calls AWS Rekognition
     ↓
DynamoDB stores labels
     ↓
Glue catalogs the data
     ↓
Athena queries it
     ↓
QuickSight visualizes it
```

---

## Key URLs

| Resource | URL |
|----------|-----|
| QuickSight | https://us-east-1.quicksight.aws.amazon.com |
| AWS Console | https://console.aws.amazon.com |
| Athena | https://console.aws.amazon.com/athena/ |
| DynamoDB | https://console.aws.amazon.com/dynamodb/ |
| Lambda Logs | https://console.aws.amazon.com/logs/ |

---

**Total Setup Time:** 5 minutes
**Status:** ✓ Ready to use
**Support:** See `DEPLOYMENT_COMPLETE.md` for full documentation
