#!/usr/bin/env python3
import json
import os
import aws_cdk as cdk
from api.infrastructure import APIStack
from integration.infrastructure import IntegrationStack
from recognition.infrastructure import RekognitionStack
from visualization.infrastructure import VisualizationStack

app = cdk.App()

# ── Account / region ───────────────────────────────────────────────────────────
# Resolved from the active AWS CLI profile at synth time.
# Candidates never need to edit this file.
ACCOUNT_ID = os.environ.get("CDK_DEFAULT_ACCOUNT") or app.account
DEFAULT_REGION = os.environ.get("CDK_DEFAULT_REGION") or app.region

env = cdk.Environment(account=ACCOUNT_ID, region=DEFAULT_REGION)

# ── Context values (override in cdk.json or with -c key=value) ────────────────
QUICKSIGHT_USER = app.node.try_get_context("quicksight_user") or "gen-ai-user"

# ── DynamoDB table name ────────────────────────────────────────────────────────
# Read from the RekognitionStack outputs file written by deploy.sh.
# This avoids hardcoding the CloudFormation-generated table name and means
# VisualizationStack always uses the currently deployed table — no manual edits.
def _read_rekognition_table_name() -> str:
    outputs_file = os.path.join(os.path.dirname(__file__), "cdk-outputs-RekognitionStack.json")
    if os.path.exists(outputs_file):
        with open(outputs_file) as f:
            outputs = json.load(f)
        table_name = (
            outputs.get("RekognitionStack", {}).get("ClassificationsTableName")
        )
        if table_name:
            return table_name
    # Fallback: let the candidate override via context
    return app.node.try_get_context("dynamodb_table_name") or ""

DYNAMODB_TABLE_NAME = _read_rekognition_table_name()

# ── Stacks ─────────────────────────────────────────────────────────────────────
apiStack = APIStack(app, "APIStack", env=env)

integrationStack = IntegrationStack(app, "IntegrationStack", env=env)

rekognitionStack = RekognitionStack(
    app,
    "RekognitionStack",
    sqs_url=apiStack.sqs_url,
    sqs_arn=apiStack.sqs_arn,
    sns_arn=integrationStack.sns_arn,
    env=env,
)

# ── VisualizationStack ─────────────────────────────────────────────────────────
# Wires the Classifications DynamoDB table (from RekognitionStack) into Athena
# federated query → Glue Data Catalog → QuickSight.
#
# Deploy RekognitionStack first — its outputs file is read above to resolve the
# table name automatically. No manual edits needed.
#
# AFTER deploying, run the Glue crawler once to populate the schema:
#   aws glue start-crawler --name dynamodb-classifications-crawler
# ──────────────────────────────────────────────────────────────────────────────
QUICKSIGHT_PRINCIPAL_ARN = (
    f"arn:aws:quicksight:{DEFAULT_REGION}:{ACCOUNT_ID}:user/default/{QUICKSIGHT_USER}"
)

visualizationStack = VisualizationStack(
    app,
    "VisualizationStack",
    # Plain string — avoids CloudFormation export locks on RekognitionStack.
    # Value is read from cdk-outputs-RekognitionStack.json at synth time,
    # or overridden with: cdk deploy -c dynamodb_table_name=MyTableName
    dynamodb_table_name=DYNAMODB_TABLE_NAME,
    dynamodb_table_arn=(
        f"arn:aws:dynamodb:{DEFAULT_REGION}:{ACCOUNT_ID}:table/{DYNAMODB_TABLE_NAME}"
        if DYNAMODB_TABLE_NAME else ""
    ),
    quicksight_principal_arn=QUICKSIGHT_PRINCIPAL_ARN,
    env=env,
)

# ── Cost tracking tag — applied to all stacks ──────────────────────────────────
for stack in [apiStack, integrationStack, rekognitionStack, visualizationStack]:
    cdk.Tags.of(stack).add("AppManagerCFNStackKey", stack.stack_name)

app.synth()
