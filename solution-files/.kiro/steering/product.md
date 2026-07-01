# Product Overview

Cloudage Image Rekognition is an AWS-based image processing pipeline that:

1. Accepts image URLs via a REST API, downloads them, and stores them in S3
2. Automatically detects labels in uploaded images using Amazon Rekognition
3. Persists classification results (image key + labels) in DynamoDB
4. Notifies downstream systems via SNS/SQS when recognition completes
5. Forwards results as XML to a third-party endpoint via an integration Lambda
6. Visualises classification data in Amazon QuickSight via Athena federated queries over DynamoDB

The system is designed as a workshop/training project. Each Lambda module contains `TODO` comments and paired `_solution.py` files that represent the completed reference implementation.
