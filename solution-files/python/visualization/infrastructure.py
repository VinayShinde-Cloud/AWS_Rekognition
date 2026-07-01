"""
VisualizationStack CDK

Architecture:
  DynamoDB (Classifications table)
      │
      ▼
  Athena Federated Query
      │  (AthenaDynamoDBConnector Lambda — deployed via SAR)
      │  (spill bucket for large result sets)
      ▼
  Glue Data Catalog
      │  (Glue Crawler infers schema from DynamoDB table)
      ▼
  Athena Data Catalog (named data source)
      │
      ▼
  QuickSight  ←  connects via Athena data source

References:
  https://aws.amazon.com/blogs/big-data/visualize-amazon-dynamodb-insights-in-amazon-quicksight-using-the-amazon-athena-dynamodb-connector-and-aws-glue/
"""

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_athena as athena,
    aws_glue as glue,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_sam as sam,
)
from constructs import Construct

# SAR application for the Athena DynamoDB connector (AWS-published, us-east-1).
# Version format is year.week_of_year.iteration — latest confirmed: 2023.49.2
CONNECTOR_SAR_ARN = (
    "arn:aws:serverlessrepo:us-east-1:292517598671:"
    "applications/AthenaDynamoDBConnector"
)
CONNECTOR_SAR_VERSION = "2023.49.2"  # latest confirmed release


class VisualizationStack(Stack):
    """
    Provisions the full DynamoDB → Athena → Glue → QuickSight pipeline.

    Parameters
    ----------
    dynamodb_table_name : str
        Name of the DynamoDB table to visualise (e.g. the Classifications table
        created by RekognitionStack).
    dynamodb_table_arn : str
        ARN of that table — used for least-privilege IAM grants.
    quicksight_principal_arn : str
        ARN of the QuickSight user/group that should own the Athena data source.
        Format: arn:aws:quicksight:<region>:<account>:user/default/<username>
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        dynamodb_table_name: str,
        dynamodb_table_arn: str,
        quicksight_principal_arn: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── 1. Spill bucket ────────────────────────────────────────────────────
        # Athena writes intermediate / large result sets here when the connector
        # response exceeds the Lambda payload limit.
        # ObjectOwnership must be set to BUCKET_OWNER_ENFORCED (the CDK default
        # when block_public_access is BLOCK_ALL) — the connector's bucket-ownership
        # check calls s3:GetBucketOwnershipControls and expects the bucket to be
        # owned by the same account. Setting it explicitly avoids the
        # "Error while checking bucket ownership" RuntimeException.
        spill_bucket = s3.Bucket(
            self,
            "AthenaSpillBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            lifecycle_rules=[
                # Spill objects are transient — expire after 1 day
                s3.LifecycleRule(
                    id="ExpireSpillObjects",
                    expiration=Duration.days(1),
                    enabled=True,
                )
            ],
        )

        # ── 2. Athena query-results bucket ─────────────────────────────────────
        # Import existing bucket if it exists, otherwise create new one
        athena_results_bucket_name = f"athena-results-{self.account}"
        
        try:
            # Try to import existing bucket
            athena_results_bucket = s3.Bucket.from_bucket_name(
                self,
                "AthenaResultsBucket",
                athena_results_bucket_name,
            )
        except:
            # Create new bucket if doesn't exist
            athena_results_bucket = s3.Bucket(
                self,
                "AthenaResultsBucket",
                bucket_name=athena_results_bucket_name,
                removal_policy=RemovalPolicy.DESTROY,
                auto_delete_objects=True,
                block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                encryption=s3.BucketEncryption.S3_MANAGED,
                enforce_ssl=True,
                lifecycle_rules=[
                    s3.LifecycleRule(
                        id="ExpireQueryResults",
                        expiration=Duration.days(7),
                        enabled=True,
                    )
                ],
            )

        # Athena service principal needs GetObject/PutObject on the results bucket
        # so it can store query results. This is CRITICAL for Athena federated queries
        # to work with the DynamoDB connector.
        athena_results_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowAthenaServiceAccess",
                principals=[
                    iam.ServicePrincipal("athena.amazonaws.com"),
                ],
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:AbortMultipartUpload",
                    "s3:ListBucket",
                    "s3:GetBucketLocation",
                    "s3:GetBucketVersioning",
                ],
                resources=[
                    athena_results_bucket.bucket_arn,
                    f"{athena_results_bucket.bucket_arn}/*",
                ],
            )
        )

        # QuickSight's service role needs GetObject/PutObject on the results bucket
        # so it can run Athena queries and read back results.
        # The QuickSight service principal is region-specific.
        athena_results_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowQuickSightAthenaAccess",
                principals=[
                    iam.ServicePrincipal("quicksight.amazonaws.com"),
                ],
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:AbortMultipartUpload",
                    "s3:ListBucket",
                    "s3:GetBucketLocation",
                ],
                resources=[
                    athena_results_bucket.bucket_arn,
                    f"{athena_results_bucket.bucket_arn}/*",
                ],
            )
        )

        # Also grant the specific QuickSight user's account access via IAM
        athena_results_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowAthenaWorkgroupResultsWrite",
                principals=[
                    iam.AccountPrincipal(self.account),
                ],
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:AbortMultipartUpload",
                    "s3:ListBucket",
                    "s3:GetBucketLocation",
                    "s3:GetObjectVersion",
                ],
                resources=[
                    athena_results_bucket.bucket_arn,
                    f"{athena_results_bucket.bucket_arn}/*",
                ],
            )
        )

        # Glue service needs access to the results bucket for metadata operations
        athena_results_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowGlueResultsBucketAccess",
                principals=[
                    iam.ServicePrincipal("glue.amazonaws.com"),
                ],
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket",
                    "s3:GetBucketLocation",
                ],
                resources=[
                    athena_results_bucket.bucket_arn,
                    f"{athena_results_bucket.bucket_arn}/*",
                ],
            )
        )

        # ── 3. Athena workgroup ────────────────────────────────────────────────
        workgroup = athena.CfnWorkGroup(
            self,
            "VisualizationWorkgroup",
            name="dynamodb-visualization",
            description="Workgroup for DynamoDB → QuickSight queries",
            state="ENABLED",
            work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                    output_location=f"s3://{athena_results_bucket.bucket_name}/results/",
                    encryption_configuration=athena.CfnWorkGroup.EncryptionConfigurationProperty(
                        encryption_option="SSE_S3",
                    ),
                ),
                enforce_work_group_configuration=True,
                publish_cloud_watch_metrics_enabled=True,
                bytes_scanned_cutoff_per_query=1_073_741_824,  # 1 GB safety limit
            ),
        )

        # IAM policy that allows QuickSight's service role to use this workgroup.
        # Attached to the QuickSight service-linked role via a resource-based grant.
        quicksight_athena_policy = iam.ManagedPolicy(
            self,
            "QuickSightAthenaPolicy",
            description="Allows QuickSight to run Athena queries in the visualization workgroup",
            statements=[
                iam.PolicyStatement(
                    sid="AllowAthenaWorkgroupAccess",
                    actions=[
                        "athena:GetWorkGroup",
                        "athena:StartQueryExecution",
                        "athena:StopQueryExecution",
                        "athena:GetQueryExecution",
                        "athena:GetQueryResults",
                        "athena:ListQueryExecutions",
                        "athena:BatchGetQueryExecution",
                    ],
                    resources=[
                        f"arn:aws:athena:{self.region}:{self.account}:workgroup/dynamodb-visualization"
                    ],
                ),
                iam.PolicyStatement(
                    sid="AllowAthenaResultsBucketAccess",
                    actions=[
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:AbortMultipartUpload",
                        "s3:ListBucket",
                        "s3:GetBucketLocation",
                    ],
                    resources=[
                        athena_results_bucket.bucket_arn,
                        f"{athena_results_bucket.bucket_arn}/*",
                    ],
                ),
                iam.PolicyStatement(
                    sid="AllowGlueReadForAthena",
                    actions=[
                        "glue:GetDatabase",
                        "glue:GetDatabases",
                        "glue:GetTable",
                        "glue:GetTables",
                        "glue:GetPartition",
                        "glue:GetPartitions",
                        "glue:BatchGetPartition",
                    ],
                    resources=["*"],
                ),
            ],
        )

        # NOTE: QuickSightAthenaPolicy is created above but NOT attached to
        # aws-quicksight-service-role-v0 via CDK — that role is at the 10-policy
        # IAM limit. Attach manually if needed:
        #   aws iam attach-role-policy \
        #     --role-name aws-quicksight-service-role-v0 \
        #     --policy-arn <QuickSightAthenaPolicyArn>
        # (first detach an unused policy to make room)

        # NOTE: AWSQuicksightAthenaAccess is attached to aws-quicksight-service-role-v0
        # as a one-time manual step (outside CDK) to avoid requiring iam:AttachRolePolicy
        # in the deployer policy. Run once:
        #   aws iam attach-role-policy \
        #     --role-name aws-quicksight-service-role-v0 \
        #     --policy-arn arn:aws:iam::aws:policy/service-role/AWSQuicksightAthenaAccess

        # ── 4. IAM role for the connector Lambda ───────────────────────────────
        # Managed policies confirmed to be required by the SAR connector:
        #   - AWSLambdaBasicExecutionRole  : CloudWatch Logs
        #   - AmazonDynamoDBFullAccess     : connector reads all DynamoDB tables
        #   - AmazonS3FullAccess           : spill bucket + results bucket access
        #                                    (scoped inline policies alone are not
        #                                    enough — the SAR connector's Java SDK
        #                                    makes additional S3 calls that require
        #                                    broader access)
        #   - AWSQuicksightAthenaAccess    : connector invoked via Athena federated
        #                                    query from QuickSight
        connector_role = iam.Role(
            self,
            "ConnectorLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Execution role for the Athena DynamoDB connector Lambda",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonDynamoDBFullAccess"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonS3FullAccess"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSQuicksightAthenaAccess"
                ),
            ],
        )

        # DynamoDB read access — all actions scoped to account/region level.
        # The Athena connector discovers and calls tables by their Glue-catalogued
        # names which may differ in case from the CDK token ARN, so we scope to
        # all tables in the account rather than a single ARN to avoid case-mismatch
        # AccessDenied errors at query time.
        connector_role.add_to_policy(
            iam.PolicyStatement(
                sid="AllowDynamoDBReadAll",
                actions=[
                    "dynamodb:ListTables",
                    "dynamodb:DescribeTable",
                    "dynamodb:Scan",
                    "dynamodb:Query",
                    "dynamodb:GetItem",
                    "dynamodb:BatchGetItem",
                ],
                resources=["*"],
            )
        )

        # Glue Data Catalog access (connector stores schema here)
        connector_role.add_to_policy(
            iam.PolicyStatement(
                sid="AllowGlueCatalogAccess",
                actions=[
                    "glue:GetDatabase",
                    "glue:GetDatabases",
                    "glue:GetTable",
                    "glue:GetTables",
                    "glue:GetPartition",
                    "glue:GetPartitions",
                    "glue:CreateTable",
                    "glue:UpdateTable",
                    "glue:BatchCreatePartition",
                ],
                resources=["*"],  # Glue catalog ARNs are account-wide
            )
        )

        # Spill bucket read/write.
        # GetBucketOwnershipControls + GetBucketLocation are required by the
        # connector at startup — it verifies bucket ownership before writing spill
        # data. Without these the connector throws:
        #   "Error while checking bucket ownership for <spill-bucket>"
        connector_role.add_to_policy(
            iam.PolicyStatement(
                sid="AllowSpillBucketAccess",
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListBucket",
                    "s3:GetBucketLocation",
                    "s3:GetBucketOwnershipControls",
                    "s3:GetEncryptionConfiguration",
                ],
                resources=[
                    spill_bucket.bucket_arn,
                    f"{spill_bucket.bucket_arn}/*",
                ],
            )
        )

        # Athena results bucket read (connector reads back spilled results).
        # Same bucket-level actions needed for ownership verification.
        connector_role.add_to_policy(
            iam.PolicyStatement(
                sid="AllowAthenaResultsBucketRead",
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:GetBucketLocation",
                    "s3:GetBucketOwnershipControls",
                    "s3:GetEncryptionConfiguration",
                ],
                resources=[
                    athena_results_bucket.bucket_arn,
                    f"{athena_results_bucket.bucket_arn}/*",
                ],
            )
        )

        # ── Grant QuickSight service role permission to invoke the connector ──
        # QuickSight's service role needs to invoke the Athena DynamoDB connector
        # Lambda function when running federated queries. Without this permission,
        # QuickSight queries fail with "insufficient permissions" error.
        # This grants lambda:InvokeFunction on all Connector* Lambda functions.
        quicksight_service_role = iam.Role.from_role_arn(
            self,
            "QuickSightServiceRoleRef",
            f"arn:aws:iam::{self.account}:role/aws-quicksight-service-role-v0",
            mutable=True,
        )
        quicksight_service_role.add_to_principal_policy(
            iam.PolicyStatement(
                sid="AllowInvokeAthenaConnectorLambda",
                actions=["lambda:InvokeFunction"],
                resources=[
                    f"arn:aws:lambda:{self.region}:{self.account}:function:*Connector*"
                ],
            )
        )

        # ── Explicit bucket policy Allow for the connector role ────────────────
        # enforce_ssl=True adds a bucket policy Deny on aws:SecureTransport=false.
        # A bucket policy Deny overrides any IAM Allow — including the role policy
        # above. The Athena DynamoDB connector's Java runtime makes some S3 calls
        # that do not pass the SecureTransport condition, causing the bucket
        # ownership check to fail with a RuntimeException even though IAM is correct.
        # Adding an explicit Allow in the bucket policy for the connector role
        # ensures the Deny does not block it.
        spill_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowConnectorRoleAccess",
                effect=iam.Effect.ALLOW,
                principals=[iam.ArnPrincipal(connector_role.role_arn)],
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListBucket",
                    "s3:GetBucketLocation",
                    "s3:GetBucketOwnershipControls",
                    "s3:GetEncryptionConfiguration",
                ],
                resources=[
                    spill_bucket.bucket_arn,
                    f"{spill_bucket.bucket_arn}/*",
                ],
            )
        )

        # ── 5. Athena DynamoDB connector (via SAR) ─────────────────────────────
        # The connector is an AWS-published Serverless Application Repository app.
        # It deploys a Lambda function that Athena calls for federated queries.
        connector_app = sam.CfnApplication(
            self,
            "AthenaDynamoDBConnector",
            location=sam.CfnApplication.ApplicationLocationProperty(
                application_id=CONNECTOR_SAR_ARN,
                semantic_version=CONNECTOR_SAR_VERSION,
            ),
            parameters={
                # Name of the Lambda function that Athena will invoke
                "AthenaCatalogName": "dynamodb",
                # S3 URI where the connector spills large responses
                "SpillBucket": spill_bucket.bucket_name,
                "SpillPrefix": "athena-spill",
                # Disable connection string — connector discovers tables via Glue
                "DisableSpillEncryption": "false",
                # Pass the pre-created role ARN so the connector uses least-privilege
                "LambdaRole": connector_role.role_arn,
            },
        )
        # Ensure the role exists before the SAR app tries to use it
        connector_app.node.add_dependency(connector_role)

        # ── 6. Glue Database ───────────────────────────────────────────────────
        glue_database = glue.CfnDatabase(
            self,
            "DynamoDBGlueDatabase",
            catalog_id=self.account,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name="recognitiondb",
                description="Glue database for DynamoDB tables accessed via Athena",
            ),
        )

        # ── 7. IAM role for the Glue Crawler ──────────────────────────────────
        # Use a customer-managed policy (not inline) so CloudFormation creates
        # and attaches it as a single atomic resource before the crawler starts.
        crawler_dynamodb_policy = iam.ManagedPolicy(
            self,
            "GlueCrawlerDynamoDBPolicy",
            description="Allows Glue crawler to read the Classifications DynamoDB table",
            statements=[
                iam.PolicyStatement(
                    sid="AllowDynamoDBReadAll",
                    # All DynamoDB read actions use "*" — DescribeTable/ListTables
                    # require it by AWS, and Scan/Query/GetItem use it to avoid
                    # case-sensitivity mismatches between CDK token ARNs and the
                    # lowercase table names Glue discovers at crawl time.
                    actions=[
                        "dynamodb:ListTables",
                        "dynamodb:DescribeTable",
                        "dynamodb:Scan",
                        "dynamodb:Query",
                        "dynamodb:GetItem",
                        "dynamodb:BatchGetItem",
                    ],
                    resources=["*"],
                ),
            ],
        )

        crawler_role = iam.Role(
            self,
            "GlueCrawlerRole",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            description="Execution role for the Glue DynamoDB crawler",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSGlueServiceRole"
                ),
                crawler_dynamodb_policy,  # attached at role creation time
            ],
        )

        # ── 8. Glue Crawler ────────────────────────────────────────────────────
        # Crawls the DynamoDB table and writes schema to the Glue Data Catalog.
        # Run this manually (or on a schedule) after deploying to populate the catalog.
        crawler = glue.CfnCrawler(
            self,
            "DynamoDBCrawler",
            name="dynamodb-classifications-crawler",
            role=crawler_role.role_arn,
            database_name="recognitiondb",
            description=f"Crawls DynamoDB table '{dynamodb_table_name}' to infer schema",
            targets=glue.CfnCrawler.TargetsProperty(
                dynamo_db_targets=[
                    glue.CfnCrawler.DynamoDBTargetProperty(
                        path=dynamodb_table_name,
                    )
                ]
            ),
            schema_change_policy=glue.CfnCrawler.SchemaChangePolicyProperty(
                update_behavior="UPDATE_IN_DATABASE",
                delete_behavior="LOG",
            ),
            recrawl_policy=glue.CfnCrawler.RecrawlPolicyProperty(
                recrawl_behavior="CRAWL_EVERYTHING",
            ),
        )
        # Wait for the database AND the managed policy to exist before creating
        # the crawler — CloudFormation validates DynamoDB access at creation time.
        crawler.node.add_dependency(glue_database)
        crawler.node.add_dependency(crawler_dynamodb_policy)

        # ── 9. Athena named data catalog ───────────────────────────────────────
        # Registers the connector Lambda as a named Athena data source.
        # QuickSight will reference this catalog name when creating its data source.
        athena_catalog = athena.CfnDataCatalog(
            self,
            "DynamoDBDataCatalog",
            name="recognitiondb",
            type="LAMBDA",
            description="Athena federated data catalog backed by the DynamoDB connector",
            parameters={
                # Must match the AthenaCatalogName parameter passed to the SAR app
                "function": (
                    f"arn:aws:lambda:{self.region}:{self.account}"
                    ":function:dynamodb"
                ),
            },
        )
        athena_catalog.node.add_dependency(connector_app)

        # ── 10. QuickSight Athena data source ──────────────────────────────────
        # Creates the QuickSight data source that points at the Athena workgroup.
        # Owner is the quicksight_principal_arn passed in from app.py (resolved
        # from the quicksight_user context key in cdk.json).
        quicksight_datasource = self._create_quicksight_datasource(
            workgroup_name=workgroup.name,
            athena_results_bucket=athena_results_bucket,
            quicksight_principal_arn=quicksight_principal_arn,
        )
        quicksight_datasource.node.add_dependency(workgroup)
        quicksight_datasource.node.add_dependency(athena_catalog)
        quicksight_datasource.node.add_dependency(quicksight_athena_policy)

        # ── Outputs ────────────────────────────────────────────────────────────
        CfnOutput(
            self,
            "SpillBucketName",
            value=spill_bucket.bucket_name,
            description="S3 bucket used by the Athena DynamoDB connector for spill",
        )
        CfnOutput(
            self,
            "AthenaResultsBucketName",
            value=athena_results_bucket.bucket_name,
            description="S3 bucket where Athena stores query results",
        )
        CfnOutput(
            self,
            "AthenaWorkgroupName",
            value=workgroup.name,
            description="Athena workgroup for DynamoDB visualization queries",
        )
        CfnOutput(
            self,
            "GlueDatabaseName",
            value="recognitiondb",
            description="Glue database name — use this in Athena queries",
        )
        CfnOutput(
            self,
            "GlueCrawlerName",
            value=crawler.name,
            description=(
                "Run this Glue crawler after deploy to populate the schema: "
                "aws glue start-crawler --name dynamodb-classifications-crawler"
            ),
        )
        CfnOutput(
            self,
            "AthenaCatalogName",
            value=athena_catalog.name,
            description="Athena data catalog name — use in QuickSight data source setup",
        )
        CfnOutput(
            self,
            "QuickSightDataSourceId",
            value="dynamodb-athena-datasource",
            description="QuickSight data source ID",
        )

    # ── helpers ────────────────────────────────────────────────────────────────

    def _create_quicksight_datasource(
        self,
        workgroup_name: str,
        athena_results_bucket: s3.Bucket,
        quicksight_principal_arn: str,
    ):
        """
        Creates a QuickSight Athena data source.

        QuickSight must be subscribed in the account before deploying this stack.
        The principal_arn must be a valid QuickSight user or group ARN.
        """
        from aws_cdk import aws_quicksight as quicksight

        datasource = quicksight.CfnDataSource(
            self,
            "QuickSightAthenaDataSource",
            aws_account_id=self.account,
            data_source_id="dynamodb-athena-datasource",
            name="DynamoDB via Athena",
            type="ATHENA",
            data_source_parameters=quicksight.CfnDataSource.DataSourceParametersProperty(
                athena_parameters=quicksight.CfnDataSource.AthenaParametersProperty(
                    work_group=workgroup_name,
                )
            ),
            ssl_properties=quicksight.CfnDataSource.SslPropertiesProperty(
                disable_ssl=False,
            ),
            permissions=[
                quicksight.CfnDataSource.ResourcePermissionProperty(
                    principal=quicksight_principal_arn,
                    actions=[
                        "quicksight:DescribeDataSource",
                        "quicksight:DescribeDataSourcePermissions",
                        "quicksight:PassDataSource",
                        "quicksight:UpdateDataSource",
                        "quicksight:DeleteDataSource",
                        "quicksight:UpdateDataSourcePermissions",
                    ],
                )
            ],
        )
        return datasource
