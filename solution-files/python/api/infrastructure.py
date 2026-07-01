from constructs import Construct
from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_apigateway as apigateway
from aws_cdk import aws_sqs as sqs
from aws_cdk import aws_sns_subscriptions as sns_subs
from aws_cdk import aws_sns as sns
from aws_cdk import aws_s3_notifications as s3n
from aws_cdk import Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_cloudwatch as cw
from aws_cdk import aws_cloudwatch_actions as cw_actions

# ── Shared constants ───────────────────────────────────────────────────────────
# Bucket names and layer key are read from CDK context (cdk.json).
# Defaults match the workshop environment but candidates can override with:
#   cdk deploy -c asset_bucket=my-bucket -c image_bucket_prefix=my-prefix
LAYER_ZIP_KEY = "requests_layer3_11.zip"  # overridden by context in __init__


class APIStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── Resolve context values ─────────────────────────────────────────────
        asset_bucket_name = (
            self.node.try_get_context("asset_bucket") or "cloudage-resources"
        )
        image_bucket_prefix = (
            self.node.try_get_context("image_bucket_prefix") or "sagemaker"
        )
        layer_zip_key = (
            self.node.try_get_context("layer_zip_key") or "requests_layer3_11.zip"
        )
        # Image bucket name follows the convention: <prefix>-<region>-<account>
        image_bucket_name = f"{image_bucket_prefix}-{self.region}-{self.account}"

        # ── S3 Image Bucket ────────────────────────────────────────────────────
        # If the bucket already exists in the account (e.g. from a previous
        # deployment or pre-existing SageMaker bucket), import it rather than
        # creating it — CloudFormation cannot create a bucket that already exists.
        # The context key 'image_bucket_exists' is set by deploy.sh at runtime.
        bucket_exists = self.node.try_get_context("image_bucket_exists") == "true"

        if bucket_exists:
            # Import the existing bucket — no CloudFormation resource created,
            # so no conflict. Event notifications are added via bucket policy
            # and SNS separately after the SNS topic is created below.
            bucket = s3.Bucket.from_bucket_name(
                self,
                "CW-Cloudage-Images",
                image_bucket_name,
            )
        else:
            # Fresh account — create the bucket with all security settings.
            bucket = s3.Bucket(
                self,
                "CW-Cloudage-Images",
                bucket_name=image_bucket_name,
                removal_policy=RemovalPolicy.RETAIN,
                block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                encryption=s3.BucketEncryption.S3_MANAGED,
                versioned=True,
                enforce_ssl=True,
            )

        # ── S3 Asset Bucket (imported — we only read from it, no notifications needed) ─
        asset_bucket = s3.Bucket.from_bucket_name(
            self, "AssetBucket", asset_bucket_name
        )

        # ── Lambda Layer ───────────────────────────────────────────────────────
        requests_layer = lambda_.LayerVersion(
            self,
            "requests_layer",
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            layer_version_name="requests_layer",
            code=lambda_.S3Code(bucket=asset_bucket, key=layer_zip_key),
            description="requests library for Python 3.11",
        )

        # ── IAM Role for ImageGetAndSaveLambda ─────────────────────────────────
        image_lambda_role = iam.Role(
            self,
            "ImageGetAndSaveLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Execution role for ImageGetAndSaveLambda",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # Least privilege — Lambda only needs to write images to S3
        image_lambda_role.add_to_policy(
            iam.PolicyStatement(
                sid="AllowS3PutObject",
                actions=["s3:PutObject"],
                resources=[bucket.bucket_arn + "/*"],
            )
        )

        # ── Lambda Function ────────────────────────────────────────────────────
        image_get_and_save_lambda = lambda_.Function(
            self,
            "ImageGetAndSaveLambda",
            function_name="ImageGetAndSaveLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            layers=[requests_layer],
            role=image_lambda_role,
            code=lambda_.Code.from_asset("api/runtime"),
            handler="get_save_image.handler",
            timeout=Duration.seconds(30),
            memory_size=256,  # CRITICAL FIX: Increased from default 128MB for network operations
            environment={"BUCKET_NAME": bucket.bucket_name},
            description="Downloads an image from a URL and saves it to S3",
            # Concurrency is throttled at the API Gateway stage level (100 rps)
            # rather than here — avoids hitting the account unreserved minimum.
        )

        # ── API Gateway ────────────────────────────────────────────────────────
        api = apigateway.RestApi(
            self,
            "REST_API",
            rest_api_name="Image Upload Service",
            cloud_watch_role=True,
            description="Cloudage - upload image service.",
            deploy_options=apigateway.StageOptions(
                logging_level=apigateway.MethodLoggingLevel.INFO,
                metrics_enabled=True,
                # Throttle at stage level — protects Lambda and downstream services
                throttling_rate_limit=100,   # steady-state requests/sec
                throttling_burst_limit=200,  # burst capacity
            ),
        )

        get_image_integration = apigateway.LambdaIntegration(
            image_get_and_save_lambda,
            request_templates={"application/json": '{ "statusCode": "200" }'},
        )

        api.root.add_method("GET", get_image_integration)

        # ── SQS Queue with DLQ ─────────────────────────────────────────────────
        upload_dlq = sqs.Queue(
            self,
            "UploadImageDLQ",
            retention_period=Duration.days(14),
        )

        upload_queue = sqs.Queue(
            self,
            "uploaded_image_queue",
            # visibility_timeout must exceed Lambda timeout to prevent duplicate
            # processing. Rule: visibility_timeout >= 6 × Lambda timeout.
            # Lambda timeout = 30s → minimum = 180s. Using 360s for headroom.
            visibility_timeout=Duration.seconds(360),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=upload_dlq,
            ),
        )

        self.upload_queue_url = upload_queue.queue_url
        self.upload_queue_arn = upload_queue.queue_arn

        # ── DLQ alarm — alert when messages land in the dead-letter queue ──────
        upload_dlq.metric_approximate_number_of_messages_visible().create_alarm(
            self,
            "UploadDLQAlarm",
            alarm_name="UploadImageDLQ-MessagesVisible",
            alarm_description="Messages in the upload image DLQ — investigate failed uploads",
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )

        # ── SNS Topic → SQS subscription ──────────────────────────────────────
        sqs_subscription = sns_subs.SqsSubscription(
            upload_queue, raw_message_delivery=True
        )

        upload_event_topic = sns.Topic(self, "uploaded_image_topic")
        upload_event_topic.add_subscription(sqs_subscription)

        # ── S3 Event Notification ──────────────────────────────────────────────
        # Only add the notification when we created the bucket (CDK requires
        # bucket ownership to add event notifications via CloudFormation).
        # For imported buckets, add the notification manually after deploy:
        #   aws s3api put-bucket-notification-configuration ...
        if not bucket_exists:
            bucket.add_event_notification(
                s3.EventType.OBJECT_CREATED_PUT, s3n.SnsDestination(upload_event_topic)
            )
        else:
            # Grant SNS permission to publish from the existing bucket
            upload_event_topic.add_to_resource_policy(
                iam.PolicyStatement(
                    sid="AllowS3BucketNotification",
                    principals=[iam.ServicePrincipal("s3.amazonaws.com")],
                    actions=["sns:Publish"],
                    resources=[upload_event_topic.topic_arn],
                    conditions={
                        "ArnLike": {
                            "aws:SourceArn": f"arn:aws:s3:::{image_bucket_name}"
                        }
                    },
                )
            )

    @property
    def sqs_url(self) -> str:
        return self.upload_queue_url

    @property
    def sqs_arn(self) -> str:
        return self.upload_queue_arn
