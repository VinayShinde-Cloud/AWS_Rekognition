# ============================================================================
# deploy-visualization.ps1 — Manual deployment script for VisualizationStack
# ============================================================================
#
# Purpose:
#   Deploys the VisualizationStack (Athena → Glue → QuickSight pipeline)
#   with manual error handling and verification steps.
#
# Prerequisites:
#   - Python venv activated: .venv\Scripts\Activate.ps1
#   - AWS CLI configured: aws configure
#   - Python 3.11+
#   - Node.js installed
#   - AWS CDK installed: npm install -g aws-cdk
#   - Dependencies installed: pip install -r requirements.txt
#   - RekognitionStack deployed first (needed for DynamoDB table)
#
# Usage:
#   .\deploy-visualization.ps1 [-Action deploy|diff|destroy] [-Region us-east-1]
#
# Environment variables (optional):
#   AWS_PROFILE     AWS CLI profile to use (default: "default")
#   AWS_REGION      AWS region (default: from aws configure)
# ============================================================================

param(
    [ValidateSet('deploy', 'diff', 'destroy')]
    [string]$Action = 'deploy',
    
    [string]$Region = '',
    
    [string]$Profile = $env:AWS_PROFILE ? $env:AWS_PROFILE : 'default'
)

# ────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────────────────────────────────

# Color codes for output
$COLOR_RESET = "`e[0m"
$COLOR_BLUE = "`e[34m"
$COLOR_GREEN = "`e[32m"
$COLOR_YELLOW = "`e[33m"
$COLOR_RED = "`e[31m"
$COLOR_BOLD = "`e[1m"

$ACCOUNT_ID = "784055307907"
$DEFAULT_REGION = "us-east-1"
$ASSET_BUCKET = "rekognition-915916"
$ATHENA_RESULTS_BUCKET = "athena-results-$ACCOUNT_ID"
$QUICKSIGHT_USER = "gen-ai-user"

# ────────────────────────────────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────────────────────────────────

function Write-Info {
    Write-Host "${COLOR_BLUE}[INFO]${COLOR_RESET}  $args" -NoNewline $false
}

function Write-Success {
    Write-Host "${COLOR_GREEN}[OK]${COLOR_RESET}    $args" -NoNewline $false
}

function Write-Warn {
    Write-Host "${COLOR_YELLOW}[WARN]${COLOR_RESET}  $args" -NoNewline $false
}

function Write-Error-Custom {
    Write-Host "${COLOR_RED}[ERROR]${COLOR_RESET} $args" -ForegroundColor Red -NoNewline $false
}

function Write-Step {
    Write-Host "`n${COLOR_BOLD}━━━ $args ━━━${COLOR_RESET}"
}

function Check-Prerequisites {
    Write-Step "Checking prerequisites"
    
    # Check AWS CLI
    if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
        Write-Error-Custom "AWS CLI not found. Please install it from https://aws.amazon.com/cli/"
        exit 1
    }
    Write-Success "AWS CLI found: $(aws --version)"
    
    # Check Python
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Error-Custom "Python not found. Please install Python 3.11+"
        exit 1
    }
    Write-Success "Python found: $(python --version)"
    
    # Check CDK
    if (-not (Get-Command cdk -ErrorAction SilentlyContinue)) {
        Write-Error-Custom "AWS CDK not found. Install with: npm install -g aws-cdk"
        exit 1
    }
    Write-Success "AWS CDK found: $(cdk --version)"
    
    # Check Node.js
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Write-Error-Custom "Node.js not found. Please install Node.js 20+"
        exit 1
    }
    Write-Success "Node.js found: $(node --version)"
}

function Check-AWS-Access {
    Write-Step "Verifying AWS access"
    
    try {
        $caller = aws sts get-caller-identity --profile $Profile | ConvertFrom-Json
        Write-Success "AWS Account: $($caller.Account)"
        Write-Success "IAM User: $($caller.Arn)"
        Write-Success "Region: $Region"
    }
    catch {
        Write-Error-Custom "Failed to authenticate with AWS. Please run: aws configure --profile $Profile"
        exit 1
    }
}

function Check-RekognitionStack-Deployed {
    Write-Step "Checking if RekognitionStack is deployed"
    
    try {
        $stack = aws cloudformation describe-stacks `
            --stack-name RekognitionStack `
            --region $Region `
            --profile $Profile 2>$null | ConvertFrom-Json
        
        if ($stack.Stacks.Count -gt 0 -and $stack.Stacks[0].StackStatus -eq "CREATE_COMPLETE") {
            Write-Success "RekognitionStack is deployed"
            return $true
        }
        else {
            Write-Warn "RekognitionStack status: $($stack.Stacks[0].StackStatus)"
            return $false
        }
    }
    catch {
        Write-Error-Custom "RekognitionStack not found. Please deploy it first."
        return $false
    }
}

function Get-DynamoDB-TableName {
    Write-Step "Reading DynamoDB table name from outputs"
    
    if (Test-Path "cdk-outputs-RekognitionStack.json") {
        $outputs = Get-Content "cdk-outputs-RekognitionStack.json" | ConvertFrom-Json
        $tableName = $outputs.RekognitionStack.ClassificationsTableName
        
        if ($tableName) {
            Write-Success "DynamoDB table: $tableName"
            return $tableName
        }
    }
    
    Write-Error-Custom "Could not find DynamoDB table name in cdk-outputs-RekognitionStack.json"
    exit 1
}

function Run-CDK-Synth {
    Write-Step "Synthesizing CloudFormation template"
    
    try {
        cdk synth VisualizationStack `
            --profile $Profile `
            --region $Region | Out-Null
        Write-Success "CDK synthesis successful"
    }
    catch {
        Write-Error-Custom "CDK synthesis failed: $_"
        exit 1
    }
}

function Run-CDK-Deploy {
    Write-Step "Deploying VisualizationStack"
    
    Write-Info "This will deploy:"
    Write-Host "  • Athena workgroup for DynamoDB queries"
    Write-Host "  • Glue database and crawler"
    Write-Host "  • S3 buckets for Athena results and spill"
    Write-Host "  • Lambda function for Athena DynamoDB connector"
    Write-Host "  • QuickSight data source"
    Write-Host ""
    
    Write-Host "Estimated cost: ~`$0.01-0.05 per month (Athena queries billed by data scanned)"
    Write-Host ""
    
    $response = Read-Host "Proceed with deployment? (yes/no)"
    if ($response -ne 'yes' -and $response -ne 'y') {
        Write-Warn "Deployment cancelled"
        exit 0
    }
    
    try {
        cdk deploy VisualizationStack `
            --profile $Profile `
            --region $Region `
            --require-approval never `
            --no-rollback
        
        Write-Success "VisualizationStack deployed successfully"
    }
    catch {
        Write-Error-Custom "Deployment failed: $_"
        exit 1
    }
}

function Run-CDK-Diff {
    Write-Step "Computing CloudFormation diff"
    
    try {
        cdk diff VisualizationStack `
            --profile $Profile `
            --region $Region
    }
    catch {
        Write-Error-Custom "Diff failed: $_"
        exit 1
    }
}

function Run-CDK-Destroy {
    Write-Step "Destroying VisualizationStack"
    
    $response = Read-Host "WARNING: This will delete all VisualizationStack resources. Proceed? (yes/no)"
    if ($response -ne 'yes' -and $response -ne 'y') {
        Write-Warn "Destruction cancelled"
        exit 0
    }
    
    try {
        cdk destroy VisualizationStack `
            --profile $Profile `
            --region $Region `
            --force
        
        Write-Success "VisualizationStack destroyed"
    }
    catch {
        Write-Error-Custom "Destruction failed: $_"
        exit 1
    }
}

function Post-Deploy-Steps {
    Write-Step "Post-deployment steps"
    
    Write-Info "1. Start Glue crawler to populate schema:"
    Write-Host "   aws glue start-crawler ``"
    Write-Host "     --name dynamodb-classifications-crawler ``"
    Write-Host "     --region $Region"
    Write-Host ""
    
    Write-Info "2. Wait ~2-3 minutes for crawler to complete, then verify in Athena:"
    Write-Host "   aws athena get-query-execution ``"
    Write-Host "     --query-execution-id <query-id> ``"
    Write-Host "     --region $Region"
    Write-Host ""
    
    Write-Info "3. Test Athena query:"
    Write-Host "   aws athena start-query-execution ``"
    Write-Host "     --query-string 'SELECT * FROM recognitiondb.classifications LIMIT 10' ``"
    Write-Host "     --query-execution-context Database=recognitiondb ``"
    Write-Host "     --result-configuration OutputLocation=s3://$ATHENA_RESULTS_BUCKET/results/ ``"
    Write-Host "     --work-group dynamodb-visualization ``"
    Write-Host "     --region $Region"
    Write-Host ""
    
    Write-Info "4. Log in to QuickSight to create dashboards:"
    Write-Host "   https://quicksight.aws.amazon.com"
    Write-Host ""
}

# ────────────────────────────────────────────────────────────────────────────
# MAIN EXECUTION
# ────────────────────────────────────────────────────────────────────────────

Write-Host "${COLOR_BOLD}"
Write-Host "╔════════════════════════════════════════════════════════╗"
Write-Host "║  Cloudage — VisualizationStack Manual Deployment      ║"
Write-Host "╚════════════════════════════════════════════════════════╝"
Write-Host "${COLOR_RESET}"

# Use provided region or default
if ([string]::IsNullOrEmpty($Region)) {
    $Region = $DEFAULT_REGION
}

Write-Host "Action: $Action"
Write-Host "Region: $Region"
Write-Host "Profile: $Profile"
Write-Host ""

# Run checks
Check-Prerequisites
Check-AWS-Access

# Main logic
if ($Action -eq 'deploy') {
    if (-not (Check-RekognitionStack-Deployed)) {
        exit 1
    }
    
    $tableName = Get-DynamoDB-TableName
    Run-CDK-Synth
    Run-CDK-Deploy
    Post-Deploy-Steps
}
elseif ($Action -eq 'diff') {
    if (-not (Check-RekognitionStack-Deployed)) {
        exit 1
    }
    
    $tableName = Get-DynamoDB-TableName
    Run-CDK-Synth
    Run-CDK-Diff
}
elseif ($Action -eq 'destroy') {
    Run-CDK-Destroy
}

Write-Success "Done!"
