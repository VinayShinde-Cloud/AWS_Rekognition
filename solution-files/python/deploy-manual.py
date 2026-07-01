#!/usr/bin/env python3
"""
deploy-manual.py — Cloudage Image Rekognition - Manual Deployment Script

This Python script provides a cross-platform alternative to deploy-manual.ps1.
It deploys all 4 CDK stacks in dependency order with error handling and setup.

Usage:
    python deploy-manual.py                    # deploy all stacks
    python deploy-manual.py --stack APIStack   # deploy single stack
    python deploy-manual.py --destroy          # destroy all stacks
    python deploy-manual.py --diff             # show changes without deploying

Prerequisites:
    - AWS CLI v2 configured (aws configure)
    - Python 3.11+ with venv activated
    - Node.js 20+ and AWS CDK CLI installed (npm install -g aws-cdk)
"""

import os
import sys
import json
import subprocess
import time
import argparse
from pathlib import Path
from typing import List, Tuple

# ── Configuration ──────────────────────────────────────────────────────────────
ACCOUNT_ID = "784055307907"
REGION = "us-east-1"
IAM_USER = "Vinay-AI"
ASSET_BUCKET = "rekognition-915916"
ATHENA_RESULTS_BUCKET = f"athena-results-{ACCOUNT_ID}"

STACKS = [
    "APIStack",
    "IntegrationStack",
    "RekognitionStack",
    "VisualizationStack",
]

# ── Colors (ANSI) ──────────────────────────────────────────────────────────────
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"

def info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.RESET}   {msg}")

def success(msg):
    print(f"{Colors.GREEN}[OK]{Colors.RESET}     {msg}")

def warn(msg):
    print(f"{Colors.YELLOW}[WARN]{Colors.RESET}   {msg}")

def error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.RESET}  {msg}", file=sys.stderr)

def step(msg):
    print(f"\n{Colors.BOLD}━━━ {msg} ━━━{Colors.RESET}")

def header(msg):
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}{msg}{Colors.RESET}")

# ── Execution Helpers ──────────────────────────────────────────────────────────
def run_cmd(cmd: str, check: bool = True) -> Tuple[int, str]:
    """Run shell command and return exit code and output."""
    info(f"Executing: {cmd}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=600
        )
        if check and result.returncode != 0:
            error(f"Command failed: {result.stderr}")
            return result.returncode, result.stderr
        return result.returncode, result.stdout
    except subprocess.TimeoutExpired:
        error(f"Command timed out (600s): {cmd}")
        return 1, ""
    except Exception as e:
        error(f"Command execution error: {e}")
        return 1, str(e)

# ── Pre-flight Checks ──────────────────────────────────────────────────────────
def test_prerequisites():
    """Verify all required tools are installed and configured."""
    step("Pre-flight Checks")

    # Check AWS CLI
    info("Checking AWS CLI...")
    rc, out = run_cmd("aws --version", check=False)
    if rc == 0:
        success(f"AWS CLI: {out.strip()}")
    else:
        error("AWS CLI not found. Install from: https://aws.amazon.com/cli/")
        sys.exit(1)

    # Check AWS credentials
    info("Checking AWS credentials...")
    rc, out = run_cmd("aws sts get-caller-identity --region " + REGION, check=False)
    if rc == 0:
        identity = json.loads(out)
        success(f"AWS Account: {identity['Account']}")
        success(f"IAM User: {identity['Arn']}")
    else:
        error("AWS credentials not configured. Run: aws configure")
        sys.exit(1)

    # Check Node.js
    info("Checking Node.js...")
    rc, out = run_cmd("node --version", check=False)
    if rc == 0:
        success(f"Node.js: {out.strip()}")
    else:
        error("Node.js not found. Install from: https://nodejs.org/")
        sys.exit(1)

    # Check CDK
    info("Checking AWS CDK...")
    rc, out = run_cmd("cdk --version", check=False)
    if rc == 0:
        success(f"AWS CDK: {out.strip()}")
    else:
        error("AWS CDK not installed. Run: npm install -g aws-cdk")
        sys.exit(1)

    # Check Python venv
    info("Checking Python virtual environment...")
    if not os.environ.get("VIRTUAL_ENV"):
        warn("Python venv not activated. Please activate manually:")
        warn("  Windows: .venv\\Scripts\\Activate.ps1")
        warn("  Linux/Mac: source .venv/bin/activate")
        sys.exit(1)
    else:
        success(f"Python venv active: {os.environ['VIRTUAL_ENV']}")

    # Check asset bucket
    info(f"Checking asset bucket: {ASSET_BUCKET}")
    rc, out = run_cmd(f"aws s3 ls s3://{ASSET_BUCKET} --region {REGION}", check=False)
    if rc == 0:
        success(f"Asset bucket accessible: s3://{ASSET_BUCKET}")
    else:
        error(f"Asset bucket not accessible: {ASSET_BUCKET}")
        sys.exit(1)

    success("All pre-flight checks passed!")

# ── Initialize CDK ────────────────────────────────────────────────────────────
def initialize_cdk():
    """Bootstrap CDK and check outputs."""
    step("CDK Bootstrap & Setup")

    info(f"Bootstrapping CDK in account {ACCOUNT_ID} / region {REGION}...")
    rc, out = run_cmd(
        f"cdk bootstrap aws://{ACCOUNT_ID}/{REGION} --region {REGION}",
        check=False
    )
    if rc == 0:
        success("CDK bootstrap complete")
    else:
        error("CDK bootstrap failed")
        sys.exit(1)

    # Check outputs files
    info("Checking CDK outputs files...")
    expected_outputs = [
        "cdk-outputs-APIStack.json",
        "cdk-outputs-IntegrationStack.json",
        "cdk-outputs-RekognitionStack.json",
    ]

    for output_file in expected_outputs:
        if os.path.exists(output_file):
            success(f"Found: {output_file}")
        else:
            warn(f"Not found (will be created): {output_file}")

# ── Deploy Stack ───────────────────────────────────────────────────────────────
def deploy_stack(stack_name: str, diff_only: bool = False) -> bool:
    """Deploy a single stack."""
    step(f"Deploying {stack_name}")

    if diff_only:
        cmd = f"cdk diff {stack_name} --region {REGION}"
    else:
        cmd = f"cdk deploy {stack_name} --require-approval never --region {REGION}"

    rc, out = run_cmd(cmd, check=False)

    if rc == 0:
        success(f"{stack_name} deployment completed successfully")
        return True
    else:
        error(f"{stack_name} deployment failed with exit code: {rc}")
        return False

# ── Deploy All Stacks ──────────────────────────────────────────────────────────
def deploy_all_stacks(diff_only: bool = False):
    """Deploy all stacks in order."""
    header("╔════════════════════════════════════════════════════╗")
    header("║   CLOUDAGE IMAGE REKOGNITION - DEPLOYMENT START   ║")
    header("╚════════════════════════════════════════════════════╝")

    failed_stacks = []
    deployed_stacks = []

    for stack_name in STACKS:
        if not deploy_stack(stack_name, diff_only):
            failed_stacks.append(stack_name)
        else:
            deployed_stacks.append(stack_name)

        # Small delay between stacks
        time.sleep(2)

    # Summary
    header("╔════════════════════════════════════════════════════╗")
    header("║              DEPLOYMENT SUMMARY                   ║")
    header("╚════════════════════════════════════════════════════╝")

    if deployed_stacks:
        success("Successfully deployed stacks:")
        for stack in deployed_stacks:
            print(f"  ✓ {stack}")

    if failed_stacks:
        error("Failed to deploy stacks:")
        for stack in failed_stacks:
            print(f"  ✗ {stack}")
        error("Deployment incomplete. Review errors above.")
        sys.exit(1)
    else:
        success("All stacks deployed successfully!")

# ── Post-Deployment Setup ──────────────────────────────────────────────────────
def post_deployment_setup():
    """Run post-deployment configuration."""
    step("Post-Deployment Setup")

    # Configure S3 event notifications
    info("Configuring S3 event notifications...")
    image_bucket = f"sagemaker-{REGION}-{ACCOUNT_ID}"

    # Get SNS topic ARN
    rc, out = run_cmd(
        f'aws cloudformation describe-stacks --stack-name APIStack '
        f'--query "Stacks[0].Outputs[?OutputKey==\'ImageUploadTopicArn\'].OutputValue" '
        f'--output text --region {REGION}',
        check=False
    )

    if rc == 0 and out.strip():
        sns_topic_arn = out.strip()
        info(f"Image bucket: {image_bucket}")
        info(f"SNS topic: {sns_topic_arn}")

        notification_config = {
            "TopicConfigurations": [
                {
                    "Id": "ImageUploadNotification",
                    "TopicArn": sns_topic_arn,
                    "Events": ["s3:ObjectCreated:Put"]
                }
            ]
        }

        # Write config to temp file
        config_file = "/tmp/s3_notification.json"
        with open(config_file, "w") as f:
            json.dump(notification_config, f)

        rc, out = run_cmd(
            f'aws s3api put-bucket-notification-configuration '
            f'--bucket {image_bucket} '
            f'--notification-configuration file://{config_file} '
            f'--region {REGION}',
            check=False
        )

        if rc == 0:
            success("S3 event notification configured")
        else:
            warn(f"S3 event notification configuration failed: {out}")

    # Start Glue crawler
    info("Starting Glue crawler (for VisualizationStack)...")
    rc, out = run_cmd(
        f'aws glue start-crawler --name dynamodb-classifications-crawler --region {REGION}',
        check=False
    )

    if rc == 0:
        success("Glue crawler started. Schema discovery in progress...")
    else:
        warn(f"Glue crawler start failed: {out}")

    info("Waiting 10 seconds for Glue crawler to initialize...")
    time.sleep(10)

# ── Destroy All Stacks ──────────────────────────────────────────────────────────
def destroy_all_stacks():
    """Destroy all stacks in reverse order."""
    header("╔════════════════════════════════════════════════════╗")
    header("║    CLOUDAGE IMAGE REKOGNITION - DESTROY START     ║")
    header("╚════════════════════════════════════════════════════╝")

    warn("This will destroy all stacks and delete resources!")
    confirm = input("Type 'yes' to confirm destruction: ")

    if confirm != "yes":
        info("Destruction cancelled.")
        sys.exit(0)

    # Destroy in reverse order
    reverse_stacks = list(reversed(STACKS))
    failed_stacks = []

    for stack_name in reverse_stacks:
        step(f"Destroying {stack_name}")

        rc, out = run_cmd(
            f"cdk destroy {stack_name} --force --region {REGION}",
            check=False
        )

        if rc == 0:
            success(f"{stack_name} destroyed")
        else:
            error(f"{stack_name} destruction failed: {out}")
            failed_stacks.append(stack_name)

        time.sleep(2)

    if failed_stacks:
        error(f"Failed to destroy stacks: {', '.join(failed_stacks)}")
        sys.exit(1)
    else:
        success("All stacks destroyed successfully!")

# ── Main ────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Cloudage Image Rekognition - Manual Deployment Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  # Deploy all stacks in order
  python deploy-manual.py

  # Deploy only APIStack
  python deploy-manual.py --stack APIStack

  # Preview changes before deploying
  python deploy-manual.py --diff

  # Destroy all stacks (reverse order)
  python deploy-manual.py --destroy

CONFIGURATION:
  Account:       %s
  Region:        %s
  IAM User:      %s
  Asset Bucket:  %s

PREREQUISITES:
  ✓ AWS CLI v2 configured (aws configure)
  ✓ Python 3.11+ with venv activated
  ✓ Node.js 20+ installed
  ✓ AWS CDK CLI installed (npm install -g aws-cdk)
        """ % (ACCOUNT_ID, REGION, IAM_USER, ASSET_BUCKET)
    )

    parser.add_argument(
        "--stack",
        type=str,
        help=f"Deploy a single stack ({', '.join(STACKS)})"
    )
    parser.add_argument(
        "--destroy",
        action="store_true",
        help="Destroy all stacks in reverse order"
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Show pending CloudFormation changes without deploying"
    )

    args = parser.parse_args()

    header("╔════════════════════════════════════════════════════╗")
    header("║   CLOUDAGE IMAGE REKOGNITION - DEPLOYMENT TOOL    ║")
    header("╚════════════════════════════════════════════════════╝")

    info(f"Account: {ACCOUNT_ID}")
    info(f"Region: {REGION}")
    info(f"IAM User: {IAM_USER}")

    if args.destroy:
        info("Mode: DESTROY")
    elif args.diff:
        info("Mode: DIFF ONLY")
    else:
        info("Mode: DEPLOY")

    if args.stack:
        info(f"Target Stack: {args.stack}")
        if args.stack not in STACKS:
            error(f"Unknown stack: {args.stack}")
            info(f"Valid stacks: {', '.join(STACKS)}")
            sys.exit(1)

    # Pre-flight checks
    test_prerequisites()

    # Initialize CDK
    initialize_cdk()

    # Deploy or destroy
    if args.destroy:
        destroy_all_stacks()
    elif args.stack:
        deploy_stack(args.stack, args.diff)
        if not args.diff:
            post_deployment_setup()
    else:
        deploy_all_stacks(args.diff)
        if not args.diff:
            post_deployment_setup()

    header("╔════════════════════════════════════════════════════╗")
    header("║              DEPLOYMENT COMPLETE!                 ║")
    header("╚════════════════════════════════════════════════════╝")

    # Print next steps
    if not args.destroy and not args.diff:
        header("NEXT STEPS:")
        info("1. Start Glue crawler (if not already running):")
        print(f"   aws glue start-crawler --name dynamodb-classifications-crawler --region {REGION}")

        info("2. Test the pipeline by uploading images:")
        print("   python send_images.py")

        info("3. View results in DynamoDB:")
        print(f"   python scan_classifications.py --region {REGION}")

        info("4. (Optional) Set up QuickSight dashboard in AWS Console")
        print("   https://console.aws.amazon.com/quicksight")

if __name__ == "__main__":
    main()
