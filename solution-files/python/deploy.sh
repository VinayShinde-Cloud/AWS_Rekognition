#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Cloudage Image Rekognition Project
# Deploys all 4 CDK stacks in dependency order with error handling.
#
# Usage:
#   ./deploy.sh                    # deploy all stacks in order
#   ./deploy.sh --stack APIStack   # deploy a single stack
#   ./deploy.sh --destroy          # destroy all stacks in reverse order
#   ./deploy.sh --diff             # show pending changes without deploying
#
# Prerequisites:
#   - AWS CLI configured (aws configure)
#   - Python venv active: source .venv/bin/activate
#
# Account, region, and IAM user are resolved automatically from the active
# AWS CLI profile — no hardcoded values needed.
# =============================================================================

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
# Account ID and region are resolved from the active AWS CLI profile at runtime.
# They are populated in preflight_checks() and used throughout the script.
ACCOUNT_ID="784055307907"
REGION="eu-north-1"
IAM_USER="Vinay-AI"
PROFILE="${AWS_PROFILE:-default}"

# Stacks in deployment order (dependencies flow downward)
STACKS=(
  "APIStack"
  "IntegrationStack"
  "RekognitionStack"
  "VisualizationStack"
)

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Colour

# ── Helpers ───────────────────────────────────────────────────────────────────
log_info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_success() { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_step()    { echo -e "\n${BOLD}━━━ $* ━━━${NC}"; }

# ── Parse arguments ───────────────────────────────────────────────────────────
MODE="deploy"
SINGLE_STACK=""
RUN_CLEANUP=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --destroy)
      MODE="destroy"
      shift
      ;;
    --diff)
      MODE="diff"
      shift
      ;;
    --cleanup)
      MODE="cleanup"
      shift
      ;;
    --stack)
      SINGLE_STACK="${2:-}"
      shift 2
      ;;
    --profile)
      PROFILE="${2:-}"
      shift 2
      ;;
    --help|-h)
      echo "Usage: $0 [--stack STACK_NAME] [--destroy] [--diff] [--cleanup] [--profile PROFILE]"
      echo ""
      echo "  --stack STACK_NAME   Deploy/diff/destroy a single stack only"
      echo "  --destroy            Destroy all stacks in reverse order"
      echo "  --diff               Show pending changes without deploying"
      echo "  --cleanup            Delete orphaned named resources from a previous deploy"
      echo "                       (Athena workgroup, Glue DB/crawler, QuickSight datasource)"
      echo "                       Run this before re-deploying into a fresh account."
      echo "  --profile PROFILE    AWS CLI profile to use (default: \$AWS_PROFILE or 'default')"
      exit 0
      ;;
    *)
      log_error "Unknown argument: $1"
      exit 1
      ;;
  esac
done

# ── Pre-flight checks ─────────────────────────────────────────────────────────
preflight_checks() {
  log_step "Pre-flight checks"

  # Check AWS CLI
  if ! command -v aws &>/dev/null; then
    log_error "AWS CLI not found. Install it: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
    exit 1
  fi
  log_success "AWS CLI found: $(aws --version 2>&1 | head -1)"

  # Check CDK
  if ! command -v cdk &>/dev/null; then
    log_error "AWS CDK not found. Install it: npm install -g aws-cdk"
    exit 1
  fi
  log_success "CDK found: $(cdk --version)"

  # Check Python venv
  if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    log_warn "No Python virtual environment active. Attempting to activate .venv..."
    if [[ -f ".venv/bin/activate" ]]; then
      # shellcheck disable=SC1091
      source .venv/bin/activate
      log_success "Activated .venv"
    else
      log_error "No .venv found. Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
      exit 1
    fi
  fi
  log_success "Python venv active: ${VIRTUAL_ENV}"

  # Check AWS credentials and resolve account/region/user from active profile
  log_info "Resolving AWS identity from profile '${PROFILE}'..."
  local caller_json
  caller_json=$(aws sts get-caller-identity --profile "${PROFILE}" --output json 2>&1) || {
    log_error "AWS credentials check failed. Run: aws configure --profile ${PROFILE}"
    exit 1
  }
  ACCOUNT_ID=$(echo "${caller_json}" | python3 -c "import sys,json; print(json.load(sys.stdin)['Account'])")
  CALLER_ARN=$(echo "${caller_json}" | python3 -c "import sys,json; print(json.load(sys.stdin)['Arn'])")

  # Resolve region from CLI config, falling back to us-east-1
  REGION=$(aws configure get region --profile "${PROFILE}" 2>/dev/null || echo "us-east-1")

  # Extract IAM username from the caller ARN (works for IAM users and assumed roles)
  IAM_USER=$(echo "${CALLER_ARN}" | python3 -c "import sys; arn=sys.stdin.read().strip(); print(arn.split('/')[-1])")

  # Export so CDK picks them up
  export CDK_DEFAULT_ACCOUNT="${ACCOUNT_ID}"
  export CDK_DEFAULT_REGION="${REGION}"

  log_success "Account  : ${ACCOUNT_ID}"
  log_success "Region   : ${REGION}"
  log_success "Identity : ${CALLER_ARN}"
}

# ── CDK Bootstrap check + auto-bootstrap ─────────────────────────────────────
# CDK requires a one-time bootstrap per account/region before any stack can be
# deployed. It creates the CDKToolkit CloudFormation stack which holds the S3
# staging bucket, ECR repo, and IAM roles that CDK uses internally.
# The SSM parameter /cdk-bootstrap/hnb659fds/version is the canonical signal
# that bootstrap has been run.
ensure_bootstrapped() {
  log_step "Checking CDK bootstrap status"

  local bootstrap_param="/cdk-bootstrap/hnb659fds/version"

  if aws ssm get-parameter \
      --name "${bootstrap_param}" \
      --region "${REGION}" \
      --profile "${PROFILE}" \
      --output text \
      --query "Parameter.Value" &>/dev/null 2>&1; then
    local version
    version=$(aws ssm get-parameter \
      --name "${bootstrap_param}" \
      --region "${REGION}" \
      --profile "${PROFILE}" \
      --output text \
      --query "Parameter.Value" 2>/dev/null)
    log_success "CDK bootstrap already done (version ${version})"
    return 0
  fi

  log_warn "CDK bootstrap not found for account ${ACCOUNT_ID} / region ${REGION}"
  log_info "Running 'cdk bootstrap' now — this is a one-time setup step..."
  log_info "It creates the CDKToolkit stack (S3 bucket + IAM roles used by CDK internally)."

  if cdk bootstrap \
      "aws://${ACCOUNT_ID}/${REGION}" \
      --profile "${PROFILE}" \
      --toolkit-stack-name CDKToolkit \
      2>&1; then
    log_success "CDK bootstrap completed successfully"
    # Fix trust policies immediately after bootstrap so the warning never appears
    log_info "Updating CDK bootstrap role trust policies for ${PROFILE} user..."
    bash "$(dirname "$0")/iam/fix-cdk-bootstrap-trust.sh" --profile "${PROFILE}" || \
      log_warn "Trust policy update failed — you may see 'could not assume role' warnings. Run: ./iam/fix-cdk-bootstrap-trust.sh"
  else
    log_error "CDK bootstrap FAILED."
    log_error ""
    log_error "Most common cause: gen-ai-user is missing the iam:CreateRole permission"
    log_error "or cannot assume the CDK bootstrap roles."
    log_error ""
    log_error "Fix: attach iam/deployer-user-policy.json to gen-ai-user, then re-run this script."
    log_error ""
    log_error "Manual command:"
    log_error "  cdk bootstrap aws://${ACCOUNT_ID}/${REGION} --profile ${PROFILE}"
    exit 1
  fi
}

# ── Ensure asset bucket exists and layer zip is uploaded ──────────────────────
# The Lambda layer zip must be in S3 before CDK can create the LayerVersion.
# This function:
#   1. Reads the bucket name from cdk.json context (asset_bucket key)
#   2. If the bucket doesn't exist, creates one with a random 3-digit suffix
#   3. Writes the new bucket name back to cdk.json so all stacks use it
#   4. Uploads requests_layer3_11.zip if not already present
ensure_asset_bucket() {
  log_step "Ensuring asset bucket and Lambda layer zip"

  local layer_zip="requests_layer3_11.zip"
  local layer_zip_path

  # Find the zip — it may be in the project root or python/ directory
  if [[ -f "${layer_zip}" ]]; then
    layer_zip_path="${layer_zip}"
  elif [[ -f "../${layer_zip}" ]]; then
    layer_zip_path="../${layer_zip}"
  else
    log_error "Cannot find ${layer_zip} — expected in python/ or project root"
    exit 1
  fi

  # Read current asset_bucket from cdk.json
  local current_bucket
  current_bucket=$(python3 -c "
import json
with open('cdk.json') as f:
    data = json.load(f)
print(data.get('context', {}).get('asset_bucket', 'cloudage-resources'))
")

  # Check if the bucket exists
  if aws s3 ls "s3://${current_bucket}" --profile "${PROFILE}" &>/dev/null 2>&1; then
    log_success "Asset bucket exists: s3://${current_bucket}"
  else
    log_warn "Bucket '${current_bucket}' not found — creating a new one..."

    # Generate a unique bucket name with a random 3-digit suffix
    local suffix
    suffix=$(python3 -c "import random; print(random.randint(100, 999))")
    local new_bucket="cloudage-resources-${suffix}"

    # Keep trying until we find an available name
    while aws s3 ls "s3://${new_bucket}" --profile "${PROFILE}" &>/dev/null 2>&1; do
      suffix=$(python3 -c "import random; print(random.randint(100, 999))")
      new_bucket="cloudage-resources-${suffix}"
    done

    log_info "Creating bucket: s3://${new_bucket} in ${REGION}..."
    aws s3 mb "s3://${new_bucket}" \
      --region "${REGION}" \
      --profile "${PROFILE}"

    # Block public access
    aws s3api put-public-access-block \
      --bucket "${new_bucket}" \
      --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" \
      --region "${REGION}" \
      --profile "${PROFILE}"

    log_success "Bucket created: s3://${new_bucket}"

    # Persist the new bucket name into cdk.json context
    python3 - <<PYEOF
import json
with open('cdk.json') as f:
    data = json.load(f)
data.setdefault('context', {})['asset_bucket'] = '${new_bucket}'
with open('cdk.json', 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
PYEOF
    log_success "Updated cdk.json: asset_bucket = ${new_bucket}"
    current_bucket="${new_bucket}"
  fi

  # Upload the layer zip if not already present
  if aws s3 ls "s3://${current_bucket}/${layer_zip}" --profile "${PROFILE}" &>/dev/null 2>&1; then
    log_success "${layer_zip} already in s3://${current_bucket}/"
  else
    log_info "Uploading ${layer_zip} to s3://${current_bucket}/..."
    aws s3 cp "${layer_zip_path}" \
      "s3://${current_bucket}/${layer_zip}" \
      --region "${REGION}" \
      --profile "${PROFILE}"
    log_success "${layer_zip} uploaded to s3://${current_bucket}/"
  fi
}
# ── Check if image bucket already exists and set CDK context ─────────────────
# CDK cannot create an S3 bucket that already exists. This function checks
# whether the image bucket (sagemaker-<region>-<account>) exists and sets
# the 'image_bucket_exists' context key so the stack can import vs create it.
ensure_image_bucket_context() {
  log_step "Checking image bucket"

  local image_bucket_prefix
  image_bucket_prefix=$(python3 -c "
import json
with open('cdk.json') as f:
    data = json.load(f)
print(data.get('context', {}).get('image_bucket_prefix', 'sagemaker'))
")
  local image_bucket="${image_bucket_prefix}-${REGION}-${ACCOUNT_ID}"
  log_info "Image bucket: s3://${image_bucket}"

  if aws s3api head-bucket --bucket "${image_bucket}" --profile "${PROFILE}" &>/dev/null 2>&1; then
    log_success "Bucket exists — will import (not recreate)"
    python3 - <<PYEOF
import json
with open('cdk.json') as f:
    data = json.load(f)
data.setdefault('context', {})['image_bucket_exists'] = 'true'
with open('cdk.json', 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
PYEOF
  else
    log_info "Bucket does not exist — will create during deploy"
    python3 - <<PYEOF
import json
with open('cdk.json') as f:
    data = json.load(f)
data.setdefault('context', {})['image_bucket_exists'] = 'false'
with open('cdk.json', 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
PYEOF
  fi
}

synth_stacks() {
  log_step "Synthesising CDK templates"
  cdk synth --profile "${PROFILE}" --quiet
  log_success "CDK synth passed — templates are valid"
}

# ── Deploy a single stack ─────────────────────────────────────────────────────
deploy_stack() {
  local stack_name="$1"
  log_step "Deploying ${stack_name}"

  if cdk deploy "${stack_name}" \
    --profile "${PROFILE}" \
    --require-approval never \
    --outputs-file "cdk-outputs-${stack_name}.json" \
    2>&1; then
    log_success "${stack_name} deployed successfully"
  else
    log_error "${stack_name} deployment FAILED"
    log_error "Check the CloudFormation console for details:"
    log_error "  https://eu-central-1.console.aws.amazon.com/cloudformation/home?region=eu-central-1#/stacks"
    exit 1
  fi
}

# ── Diff a single stack ───────────────────────────────────────────────────────
diff_stack() {
  local stack_name="$1"
  log_step "Diff for ${stack_name}"
  cdk diff "${stack_name}" --profile "${PROFILE}" || true
}

# ── Destroy a single stack ────────────────────────────────────────────────────
destroy_stack() {
  local stack_name="$1"
  log_step "Destroying ${stack_name}"
  log_warn "This will DELETE ${stack_name} and all its resources (except RETAIN-policy resources)."

  if cdk destroy "${stack_name}" \
    --profile "${PROFILE}" \
    --force \
    2>&1; then
    log_success "${stack_name} destroyed"
  else
    log_error "${stack_name} destroy FAILED — check CloudFormation console"
    exit 1
  fi
}

# ── Pre-deploy cleanup of orphaned named resources ───────────────────────────
# These resources have hardcoded names in the CDK code. If they exist in the
# account outside of CloudFormation state (e.g. from a previous manual deploy
# or a stack that was deleted without destroying resources), CDK will fail with
# "resource already exists". This function deletes them so CDK can recreate them.
#
# Safe to run even if the resources don't exist — all commands use || true.
cleanup_orphaned_resources() {
  log_step "Cleaning up orphaned named resources from previous deployments"
  log_warn "This removes resources that exist outside CloudFormation state."
  log_warn "It is safe — CDK will recreate them during deploy."
  echo ""

  # 1. Athena workgroup — use --recursive-delete-option to remove saved queries
  # before deletion. Without this flag AWS returns 400 "WorkGroup is not empty"
  # if any named queries exist in the workgroup.
  log_info "Deleting Athena workgroup 'dynamodb-visualization' (if exists)..."
  aws athena delete-work-group \
    --work-group "dynamodb-visualization" \
    --recursive-delete-option \
    --region "${REGION}" \
    --profile "${PROFILE}" 2>/dev/null \
    && log_success "Athena workgroup deleted" \
    || log_info "Athena workgroup not found — skipping"

  # 2. Athena data catalog
  log_info "Deleting Athena data catalog 'recognitiondb' (if exists)..."
  aws athena delete-data-catalog \
    --name "recognitiondb" \
    --region "${REGION}" \
    --profile "${PROFILE}" 2>/dev/null \
    && log_success "Athena data catalog deleted" \
    || log_info "Athena data catalog not found — skipping"

  # 3. Glue crawler (must stop it first if running)
  log_info "Stopping Glue crawler 'dynamodb-classifications-crawler' (if running)..."
  aws glue stop-crawler \
    --name "dynamodb-classifications-crawler" \
    --region "${REGION}" \
    --profile "${PROFILE}" 2>/dev/null || true

  log_info "Deleting Glue crawler 'dynamodb-classifications-crawler' (if exists)..."
  aws glue delete-crawler \
    --name "dynamodb-classifications-crawler" \
    --region "${REGION}" \
    --profile "${PROFILE}" 2>/dev/null \
    && log_success "Glue crawler deleted" \
    || log_info "Glue crawler not found — skipping"

  # 4. Glue database (deletes all tables inside it too)
  log_info "Deleting Glue database 'recognitiondb' (if exists)..."
  aws glue delete-database \
    --catalog-id "${ACCOUNT_ID}" \
    --name "recognitiondb" \
    --region "${REGION}" \
    --profile "${PROFILE}" 2>/dev/null \
    && log_success "Glue database deleted" \
    || log_info "Glue database not found — skipping"

  # 5. QuickSight data source
  log_info "Deleting QuickSight data source 'dynamodb-athena-datasource' (if exists)..."
  aws quicksight delete-data-source \
    --aws-account-id "${ACCOUNT_ID}" \
    --data-source-id "dynamodb-athena-datasource" \
    --region "${REGION}" \
    --profile "${PROFILE}" 2>/dev/null \
    && log_success "QuickSight data source deleted" \
    || log_info "QuickSight data source not found — skipping"

  # 6. Lambda function 'dynamodb' deployed by the SAR connector
  log_info "Deleting SAR connector Lambda 'dynamodb' (if exists)..."
  aws lambda delete-function \
    --function-name "dynamodb" \
    --region "${REGION}" \
    --profile "${PROFILE}" 2>/dev/null \
    && log_success "SAR connector Lambda deleted" \
    || log_info "SAR connector Lambda not found — skipping"

  echo ""
  log_success "Cleanup complete — ready for a fresh deploy"
}

# ── Post-deploy: run Glue crawler ─────────────────────────────────────────────
run_glue_crawler() {
  log_step "Starting Glue crawler to populate Athena schema"
  log_info "Crawler: dynamodb-classifications-crawler"

  if aws glue start-crawler \
    --name "dynamodb-classifications-crawler" \
    --region "${REGION}" \
    --profile "${PROFILE}" 2>&1; then
    log_success "Glue crawler started. It will run for ~1-2 minutes."
    log_info "Check status: aws glue get-crawler --name dynamodb-classifications-crawler --region ${REGION} --query 'Crawler.State'"
  else
    log_warn "Could not start Glue crawler (it may already be running, or VisualizationStack was not deployed)."
    log_warn "Start it manually: aws glue start-crawler --name dynamodb-classifications-crawler --region ${REGION}"
  fi
}

# ── Print outputs summary ─────────────────────────────────────────────────────
print_outputs() {
  log_step "Deployment Summary"
  echo ""
  echo -e "${BOLD}Stack outputs saved to:${NC}"
  for stack in "${STACKS[@]}"; do
    if [[ -f "cdk-outputs-${stack}.json" ]]; then
      echo "  cdk-outputs-${stack}.json"
    fi
  done
  echo ""
  echo -e "${BOLD}Next steps:${NC}"
  echo "  1. Wait ~2 minutes for the Glue crawler to finish"
  echo "  2. Open QuickSight and verify the 'DynamoDB via Athena' data source"
  echo "  3. Seed test data: python scan_classifications.py --seed --region ${REGION}"
  echo "  4. Scan the table:  python scan_classifications.py --region ${REGION}"
  echo ""
  echo -e "${BOLD}Useful links:${NC}"
  echo "  CloudFormation: https://${REGION}.console.aws.amazon.com/cloudformation/home?region=${REGION}#/stacks"
  echo "  Lambda:         https://${REGION}.console.aws.amazon.com/lambda/home?region=${REGION}#/functions"
  echo "  DynamoDB:       https://${REGION}.console.aws.amazon.com/dynamodbv2/home?region=${REGION}#tables"
  echo "  Glue:           https://${REGION}.console.aws.amazon.com/glue/home?region=${REGION}#/catalog/crawlers"
  echo "  QuickSight:     https://${REGION}.quicksight.aws.amazon.com/"
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
  echo ""
  echo -e "${BOLD}╔══════════════════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}║   Cloudage Image Rekognition — CDK Deploy Script     ║${NC}"
  echo -e "${BOLD}║   Account: ${ACCOUNT_ID}  Region: ${REGION}       ║${NC}"
  echo -e "${BOLD}╚══════════════════════════════════════════════════════╝${NC}"
  echo ""

  preflight_checks
  ensure_bootstrapped
  ensure_asset_bucket

  # Fix CDK bootstrap role trust policies so the 'could not assume role' warning
  # never appears. Safe to run on every deploy — it's idempotent (skips if already trusted).
  log_step "Fixing CDK bootstrap role trust policies"
  bash "$(dirname "$0")/iam/fix-cdk-bootstrap-trust.sh" \
    --account "${ACCOUNT_ID}" \
    --user "${IAM_USER}" \
    --profile "${PROFILE}" \
    && log_success "CDK bootstrap trust policies up to date" \
    || log_warn "Trust policy fix failed — deploy will continue but you may see 'could not assume role' warnings"

  # ── Single stack mode ──────────────────────────────────────────────────────
  if [[ -n "${SINGLE_STACK}" ]]; then
    # Validate the stack name
    VALID=false
    for s in "${STACKS[@]}"; do
      [[ "${s}" == "${SINGLE_STACK}" ]] && VALID=true && break
    done
    if [[ "${VALID}" == "false" ]]; then
      log_error "Unknown stack: ${SINGLE_STACK}"
      log_error "Valid stacks: ${STACKS[*]}"
      exit 1
    fi

    case "${MODE}" in
      deploy)  ensure_image_bucket_context; synth_stacks; ensure_asset_bucket; deploy_stack "${SINGLE_STACK}" ;;
      diff)    diff_stack "${SINGLE_STACK}" ;;
      destroy) destroy_stack "${SINGLE_STACK}" ;;
    esac
    exit 0
  fi

  # ── All stacks mode ────────────────────────────────────────────────────────
  case "${MODE}" in
    cleanup)
      preflight_checks
      cleanup_orphaned_resources
      ;;

    deploy)
      ensure_image_bucket_context
      synth_stacks
      cleanup_orphaned_resources
      log_info "Deploying ${#STACKS[@]} stacks in dependency order..."
      for stack in "${STACKS[@]}"; do
        deploy_stack "${stack}"
      done
      run_glue_crawler
      print_outputs

      # ── Attach AWSQuicksightAthenaAccess to QuickSight service role ────────
      # Required for QuickSight to run federated Athena queries via the
      # DynamoDB connector. Done via CLI (not CDK) to avoid creating extra
      # AwsCustomResource Lambda functions in the account.
      log_step "Attaching AWSQuicksightAthenaAccess to QuickSight service role"
      aws iam attach-role-policy \
        --role-name "aws-quicksight-service-role-v0" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSQuicksightAthenaAccess" \
        --profile "${PROFILE}" 2>/dev/null \
        && log_success "AWSQuicksightAthenaAccess attached to aws-quicksight-service-role-v0" \
        || log_info "AWSQuicksightAthenaAccess already attached or QuickSight not subscribed — skipping"

      log_success "All stacks deployed successfully!"

      # ── Final stack status summary ─────────────────────────────────────────
      echo ""
      log_step "Stack Status Summary"
      aws cloudformation describe-stacks \
        --region "${REGION}" \
        --profile "${PROFILE}" \
        --query "Stacks[*].[StackName,StackStatus]" \
        --output table 2>&1
      ;;

    diff)
      ensure_bootstrapped
      synth_stacks
      for stack in "${STACKS[@]}"; do
        diff_stack "${stack}"
      done
      ;;

    destroy)
      ensure_bootstrapped
      log_warn "Destroying ALL stacks in reverse order!"
      log_warn "Resources with RemovalPolicy.RETAIN (S3 buckets, DynamoDB table) will NOT be deleted."
      echo -n "Type 'yes' to confirm: "
      read -r CONFIRM
      if [[ "${CONFIRM}" != "yes" ]]; then
        log_info "Aborted."
        exit 0
      fi
      # Clean up named resources first — Athena workgroup delete fails if it
      # contains saved queries (AWS returns 400 "WorkGroup is not empty").
      # Running cleanup before CDK destroy ensures CloudFormation can delete it.
      cleanup_orphaned_resources
      # Reverse order
      for (( i=${#STACKS[@]}-1; i>=0; i-- )); do
        destroy_stack "${STACKS[$i]}"
      done
      log_success "All stacks destroyed."
      ;;
  esac
}

main "$@"
