"""
RekognitionStack CDK
"""
from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_dynamodb as ddb,
    aws_apigateway as apigateway,
    Stack,
)
from constructs import Construct

# ── Shared constants ───────────────────────────────────────────────────────────
# IMAGE_BUCKET_NAME is resolved at stack init time using self.account / self.region
# so it works in any account without hardcoding.


class RekognitionStack(Stack):
    """
    RekognitionStack — processes uploaded images via Rekognition,
    stores labels in DynamoDB, and publishes results to SNS.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        sqs_url: str,
        sqs_arn: str,
        sns_arn: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Image bucket name follows the convention: sagemaker-<region>-<account>
        # Uses self.account / self.region so it resolves correctly in any account.
        image_bucket_prefix = (
            self.node.try_get_context("image_bucket_prefix") or "sagemaker"
        )
        image_bucket_name = f"{image_bucket_prefix}-{self.region}-{self.account}"

        # ── DynamoDB Table ─────────────────────────────────────────────────────
        table = ddb.Table(
            self,
            "Classifications",
            partition_key=ddb.Attribute(name="image", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # ── IAM Role for image_recognition Lambda ──────────────────────────────
        rekognition_role = iam.Role(
            self,
            "ImageRecognitionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Execution role for image_recognition Lambda",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaSQSQueueExecutionRole"
                ),
            ],
        )

        rekognition_role.add_to_policy(
            iam.PolicyStatement(
                sid="AllowRekognitionDetectLabels",
                actions=["rekognition:DetectLabels"],
                resources=["*"],  # Rekognition has no resource-level restrictions
            )
        )

        rekognition_role.add_to_policy(
            iam.PolicyStatement(
                sid="AllowDynamoDBWrite",
                actions=["dynamodb:PutItem"],
                resources=[table.table_arn],
            )
        )

        rekognition_role.add_to_policy(
            iam.PolicyStatement(
                sid="AllowSNSPublish",
                actions=["sns:Publish"],
                resources=[sns_arn],
            )
        )

        rekognition_role.add_to_policy(
            iam.PolicyStatement(
                sid="AllowS3GetObject",
                actions=["s3:GetObject"],
                resources=[f"arn:aws:s3:::{image_bucket_name}/*"],
            )
        )

        # ── image_recognition Lambda ───────────────────────────────────────────
        lambda_function = _lambda.Function(
            self,
            "image_recognition",
            function_name="image_recognition",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="image_recognition.handler",
            role=rekognition_role,
            code=_lambda.Code.from_asset("recognition/runtime"),
            timeout=Duration.seconds(300),
            memory_size=512,  # CRITICAL FIX: Increased from default 128MB for Rekognition processing
            environment={
                "TABLE_NAME": table.table_name,
                "SQS_QUEUE_URL": sqs_url,
                "TOPIC_ARN": sns_arn,
            },
            description="Runs Rekognition on uploaded images and stores labels in DynamoDB",
        )

        lambda_function.add_event_source_mapping(
            "ImgRekognitionLambdaESM",
            event_source_arn=sqs_arn,
            batch_size=1,
        )

        # ── IAM Role for ListImagesLambda ──────────────────────────────────────
        list_images_role = iam.Role(
            self,
            "ListImagesLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Execution role for ListImagesLambda",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # Explicit DynamoDB Scan + read permissions for list_images Lambda
        list_images_role.add_to_policy(
            iam.PolicyStatement(
                sid="AllowDynamoDBScanAndRead",
                actions=[
                    "dynamodb:Scan",
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:BatchGetItem",
                    "dynamodb:DescribeTable",
                ],
                resources=[table.table_arn],
            )
        )

        # ── ListImages Lambda ──────────────────────────────────────────────────
        list_img_lambda = _lambda.Function(
            self,
            "ListImagesLambda",
            function_name="ListImagesLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            role=list_images_role,
            code=_lambda.Code.from_asset("recognition/runtime"),
            handler="list_images.handler",
            timeout=Duration.seconds(30),
            environment={"TABLE_NAME": table.table_name},
            description="Lists all classified images from DynamoDB",
        )

        # ── API Gateway ────────────────────────────────────────────────────────
        api = apigateway.RestApi(
            self,
            "REST_API",
            rest_api_name="List Images Service",
            cloud_watch_role=True,
            description="Cloudage - list images recognized service.",
            deploy_options=apigateway.StageOptions(
                logging_level=apigateway.MethodLoggingLevel.INFO,
                metrics_enabled=True,
            ),
        )

        list_images_integration = apigateway.LambdaIntegration(
            list_img_lambda,
            request_templates={"application/json": '{ "statusCode": "200" }'},
        )

        api.root.add_method("GET", list_images_integration)

        # ── Outputs ────────────────────────────────────────────────────────────
        # Export the table name and ARN so VisualizationStack can reference them
        # without relying on CDK cross-stack tokens (which create export locks).
        # After deploying RekognitionStack, copy these values into app.py.
        CfnOutput(
            self,
            "ClassificationsTableName",
            value=table.table_name,
            description="DynamoDB Classifications table name — use in VisualizationStack",
        )
        CfnOutput(
            self,
            "ClassificationsTableArn",
            value=table.table_arn,
            description="DynamoDB Classifications table ARN — use in VisualizationStack",
        )
