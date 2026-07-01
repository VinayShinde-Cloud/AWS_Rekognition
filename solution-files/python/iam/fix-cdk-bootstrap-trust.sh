#!/usr/bin/env bash
# =============================================================================
# fix-cdk-bootstrap-trust.sh
#
# Adds gen-ai-user (or any IAM user) to the trust policy of the 4 CDK bootstrap
# roles so that CDK can assume them during cdk deploy.
#
# Without this, CDK prints:
#   "current credentials could not be used to assume
#    'arn:aws:iam::ACCOUNT:role/cdk-hnb659fds-*-role-*', but are for the
#    right account. Proceeding anyway."
#
# CDK still works without this (it falls back to direct credentials), but the
# warning is noisy and the deployment is not using the intended CDK path.
#
# Usage:
#   ./iam/fix-cdk-bootstrap-trust.sh
#   ./iam/fix-cdk-bootstrap-trust.sh --user my-other-user --profile my-profile
#
# Prerequisites:
#   - AWS CLI configured
#   - The caller must have iam:GetRole + iam:UpdateAssumeRolePolicy permissions
# =============================================================================

set -euo pipefail

# ── Defaults — resolved from active AWS CLI profile if not overridden ─────────
ACCOUNT_ID=""
REGION=""
IAM_USER=""
PROFILE="${AWS_PROFILE:-default}"

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_success() { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── Parse args ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --user)    IAM_USER="${2:-}";    shift 2 ;;
    --profile) PROFILE="${2:-}";    shift 2 ;;
    --account) ACCOUNT_ID="${2:-}"; shift 2 ;;
    --region)  REGION="${2:-}";     shift 2 ;;
    --help|-h)
      echo "Usage: $0 [--user IAM_USER] [--profile PROFILE] [--account ACCOUNT_ID] [--region REGION]"
      echo "  --user     IAM username to trust (default: resolved from active profile)"
      echo "  --profile  AWS CLI profile (default: \$AWS_PROFILE or 'default')"
      echo "  --account  AWS account ID (default: resolved from active profile)"
      echo "  --region   AWS region (default: resolved from active profile)"
      exit 0 ;;
    *) log_error "Unknown argument: $1"; exit 1 ;;
  esac
done

# ── Resolve any unset values from the active AWS CLI profile ──────────────────
log_info "Resolving AWS identity from profile '${PROFILE}'..."
CALLER_JSON=$(aws sts get-caller-identity --profile "${PROFILE}" --output json 2>&1) || {
  log_error "AWS credentials check failed. Run: aws configure --profile ${PROFILE}"
  exit 1
}

if [[ -z "${ACCOUNT_ID}" ]]; then
  ACCOUNT_ID=$(echo "${CALLER_JSON}" | python3 -c "import sys,json; print(json.load(sys.stdin)['Account'])")
fi

if [[ -z "${REGION}" ]]; then
  REGION=$(aws configure get region --profile "${PROFILE}" 2>/dev/null || echo "us-east-1")
fi

if [[ -z "${IAM_USER}" ]]; then
  CALLER_ARN=$(echo "${CALLER_JSON}" | python3 -c "import sys,json; print(json.load(sys.stdin)['Arn'])")
  IAM_USER=$(echo "${CALLER_ARN}" | python3 -c "import sys; arn=sys.stdin.read().strip(); print(arn.split('/')[-1])")
fi

USER_ARN="arn:aws:iam::${ACCOUNT_ID}:user/${IAM_USER}"

# The 4 CDK bootstrap roles that need to trust the deployer user

# The 4 CDK bootstrap roles that need to trust the deployer user
CDK_ROLES=(
  "cdk-hnb659fds-deploy-role-${ACCOUNT_ID}-${REGION}"
  "cdk-hnb659fds-file-publishing-role-${ACCOUNT_ID}-${REGION}"
  "cdk-hnb659fds-image-publishing-role-${ACCOUNT_ID}-${REGION}"
  "cdk-hnb659fds-lookup-role-${ACCOUNT_ID}-${REGION}"
)

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   CDK Bootstrap Trust Policy Fix                     ║${NC}"
echo -e "${BOLD}║   Adding ${IAM_USER} to CDK bootstrap roles      ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
log_info "User ARN : ${USER_ARN}"
log_info "Profile  : ${PROFILE}"
log_info "Account  : ${ACCOUNT_ID}"
log_info "Region   : ${REGION}"
echo ""

# ── Process each role ─────────────────────────────────────────────────────────
update_trust_policy() {
  local role_name="$1"

  log_info "Processing role: ${role_name}"

  # Get current trust policy
  local current_trust
  current_trust=$(aws iam get-role \
    --role-name "${role_name}" \
    --profile "${PROFILE}" \
    --query "Role.AssumeRolePolicyDocument" \
    --output json 2>&1) || {
    log_warn "  Role not found — skipping (run cdk bootstrap first if this is a fresh account)"
    return 0
  }

  # Check if user is already trusted
  if echo "${current_trust}" | grep -q "${USER_ARN}"; then
    log_success "  ${IAM_USER} already trusted — no change needed"
    return 0
  fi

  # Add the user principal to the existing trust policy using Python
  # (avoids jq dependency and handles the JSON safely)
  local updated_trust
  updated_trust=$(python3 - <<PYEOF
import json, sys

trust = json.loads('''${current_trust}''')

new_statement = {
    "Sid": "AllowDeployerUserAssume",
    "Effect": "Allow",
    "Principal": {
        "AWS": "${USER_ARN}"
    },
    "Action": "sts:AssumeRole"
}

# Only add if not already present
arns = []
for stmt in trust.get("Statement", []):
    p = stmt.get("Principal", {})
    if isinstance(p, dict):
        aws = p.get("AWS", [])
        if isinstance(aws, str):
            arns.append(aws)
        else:
            arns.extend(aws)
    elif isinstance(p, str):
        arns.append(p)

if "${USER_ARN}" not in arns:
    trust["Statement"].append(new_statement)

print(json.dumps(trust))
PYEOF
)

  # Apply the updated trust policy
  aws iam update-assume-role-policy \
    --role-name "${role_name}" \
    --policy-document "${updated_trust}" \
    --profile "${PROFILE}" 2>&1 || {
    log_error "  Failed to update trust policy for ${role_name}"
    log_error "  Make sure your credentials have iam:UpdateAssumeRolePolicy permission"
    return 1
  }

  log_success "  Trust policy updated — ${IAM_USER} can now assume this role"
}

for role in "${CDK_ROLES[@]}"; do
  update_trust_policy "${role}"
done

echo ""
log_success "Done. Re-run your CDK deploy — the warning should be gone."
echo ""
echo -e "${BOLD}Verify with:${NC}"
echo "  aws iam get-role --role-name cdk-hnb659fds-deploy-role-${ACCOUNT_ID}-${REGION} \\"
echo "    --query 'Role.AssumeRolePolicyDocument' --output json"
