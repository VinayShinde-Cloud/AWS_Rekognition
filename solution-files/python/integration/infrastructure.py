from constructs import Construct
from aws_cdk import Stack, Duration, RemovalPolicy
from aws_cdk import aws_sqs as sqs
from aws_cdk import aws_sns_subscriptions as sns_subs
from aws_cdk import aws_sns as sns
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ssm as ssm
from aws_cdk import aws_apigateway as apigateway
from aws_cdk import aws_cloudwatch as cw

# ── Shared constants ───────────────────────────────────────────────────────────
# S3 key where SaveXMLLambda stores received XML payloads
XML_FILE_PATH = "received/payload.xml"


class IntegrationStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── Resolve context values ─────────────────────────────────────────────
        asset_bucket_name = (
            self.node.try_get_context("asset_bucket") or "cloudage-resources"
        )
        layer_zip_key = (
            self.node.try_get_context("layer_zip_key") or "requests_layer3_11.zip"
        )

        # ── S3 Bucket for SaveXMLLambda ────────────────────────────────────────
        # Stores the XML payloads POSTed by the send_email Lambda
        xml_bucket = s3.Bucket(
            self,
            "XMLPayloadBucket",
            removal_policy=RemovalPolicy.RETAIN,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            enforce_ssl=True,
        )

        # ── IAM Role for SaveXMLLambda ─────────────────────────────────────────
        save_xml_role = iam.Role(
            self,
            "SaveXMLLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Execution role for SaveXMLLambda",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # Least privilege — only needs to write XML to the bucket
        save_xml_role.add_to_policy(
            iam.PolicyStatement(
                sid="AllowS3PutXML",
                actions=["s3:PutObject"],
                resources=[xml_bucket.bucket_arn + "/*"],
            )
        )

        # ── SaveXMLLambda ──────────────────────────────────────────────────────
        # Receives XML via HTTP POST from send_email Lambda and saves to S3
        save_xml_lambda = lambda_.Function(
            self,
            "SaveXMLLambda",
            function_name="SaveXMLLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            role=save_xml_role,
            handler="SaveXMLLambda.handler",
            code=lambda_.Code.from_asset("integration/runtime"),
            timeout=Duration.seconds(30),
            environment={
                "BUCKET_NAME": xml_bucket.bucket_name,
                "FILE_PATH": XML_FILE_PATH,
            },
            description="Receives XML payload via API Gateway POST and saves it to S3",
        )

        # ── API Gateway for SaveXMLLambda ──────────────────────────────────────
        xml_api = apigateway.RestApi(
            self,
            "XMLReceiverAPI",
            rest_api_name="XML Receiver Service",
            cloud_watch_role=True,
            description="Receives XML payloads from the integration Lambda",
            deploy_options=apigateway.StageOptions(
                logging_level=apigateway.MethodLoggingLevel.INFO,
                metrics_enabled=True,
            ),
        )

        xml_integration = apigateway.LambdaIntegration(
            save_xml_lambda,
            request_templates={"application/xml": '{ "statusCode": "200" }'},
        )

        # POST / → SaveXMLLambda
        xml_api.root.add_method("POST", xml_integration)

        # ── SSM Parameter ──────────────────────────────────────────────────────
        # Points to the pre-existing 3rdPartyServer API Gateway (SaveXMLLambda).
        # Falls back to the CDK-created XMLReceiverAPI url if no context value given.
        # Override at deploy time: cdk deploy -c thirdparty_endpoint=https://...
        thirdparty_endpoint = (
            self.node.try_get_context("thirdparty_endpoint") or xml_api.url
        )

        endpoint_parameter = ssm.StringParameter(
            self,
            "ThirdPartyEndpointParameter",
            parameter_name="thirdparty_endpoint",
            string_value=thirdparty_endpoint,
            description="HTTP endpoint for the XML receiver (SaveXMLLambda via API Gateway)",
            tier=ssm.ParameterTier.STANDARD,
        )

        # ── SQS Queue with DLQ ─────────────────────────────────────────────────
        rekognized_dlq = sqs.Queue(
            self,
            "RekognizedImageDLQ",
            retention_period=Duration.days(14),
        )

        rekognized_queue = sqs.Queue(
            self,
            "rekognized_image_queue",
            # visibility_timeout >= 6 × Lambda timeout (300s) → minimum 1800s.
            # Using 1800s (30 min) to prevent duplicate processing.
            visibility_timeout=Duration.seconds(1800),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=rekognized_dlq,
            ),
        )

        # ── DLQ alarm ──────────────────────────────────────────────────────────
        rekognized_dlq.metric_approximate_number_of_messages_visible().create_alarm(
            self,
            "RekognizedDLQAlarm",
            alarm_name="RekognizedImageDLQ-MessagesVisible",
            alarm_description="Messages in the rekognized image DLQ — investigate failed integration",
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )

        # ── SNS Topic → SQS subscription ──────────────────────────────────────
        sqs_subscription = sns_subs.SqsSubscription(
            rekognized_queue, raw_message_delivery=True
        )

        rekognized_event_topic = sns.Topic(self, "rekognized_image_topic")
        self.rekognized_event_topic_arn = rekognized_event_topic.topic_arn
        rekognized_event_topic.add_subscription(sqs_subscription)

        # ── Lambda Layer (requests) ────────────────────────────────────────────
        asset_bucket = s3.Bucket.from_bucket_name(
            self, "AssetBucket", asset_bucket_name
        )

        requests_layer = lambda_.LayerVersion(
            self,
            "requests_layer",
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            layer_version_name="requests_layer_integration",
            code=lambda_.S3Code(bucket=asset_bucket, key=layer_zip_key),
            description="requests library for Python 3.11 (integration stack)",
        )

        # ── IAM Role for IntegrationLambda (send_email) ────────────────────────
        integration_lambda_role = iam.Role(
            self,
            "IntegrationLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Execution role for IntegrationLambda",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaSQSQueueExecutionRole"
                ),
            ],
        )

        # Scoped SSM read — only the endpoint parameter
        integration_lambda_role.add_to_policy(
            iam.PolicyStatement(
                sid="AllowSSMGetParameter",
                actions=["ssm:GetParameter"],
                resources=[endpoint_parameter.parameter_arn],
            )
        )

        # ── IntegrationLambda (send_email) ─────────────────────────────────────
        # Triggered by SQS, converts rekognition results to XML, POSTs to SaveXMLLambda
        integration_lambda = lambda_.Function(
            self,
            "IntegrationLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            layers=[requests_layer],
            role=integration_lambda_role,
            handler="send_email.handler",
            code=lambda_.Code.from_asset("integration/runtime"),
            timeout=Duration.seconds(300),
            description="Converts rekognition results to XML and POSTs to SaveXMLLambda",
        )

        integration_lambda.add_event_source_mapping(
            "IntegrationLambdaESM",
            event_source_arn=rekognized_queue.queue_arn,
            batch_size=1,
        )

    @property
    def sns_arn(self) -> str:
        return self.rekognized_event_topic_arn
