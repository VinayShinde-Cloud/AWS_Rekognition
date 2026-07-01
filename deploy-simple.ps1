Write-Host "Starting Cloudage deploy..." -ForegroundColor Cyan

# Navigate to the python directory
$pythonDir = Join-Path -Path $PSScriptRoot -ChildPath "solution-files" | Join-Path -ChildPath "python"
if (-not (Test-Path $pythonDir)) {
    Write-Host "ERROR: Cannot find $pythonDir" -ForegroundColor Red
    exit 1
}
Set-Location $pythonDir
Write-Host "Working directory: $pythonDir" -ForegroundColor Cyan

# Check prereqs
Write-Host "`n[1] Checking prerequisites..." -ForegroundColor Yellow
aws --version
cdk --version

# Get account info
Write-Host "`n[2] Getting AWS account..." -ForegroundColor Yellow
$identity = aws sts get-caller-identity --output json | ConvertFrom-Json
$ACCOUNT = $identity.Account
$REGION = "us-east-1"
Write-Host "Account: $ACCOUNT"
Write-Host "Region: $REGION"

# Check CDK bootstrap
Write-Host "`n[3] Checking CDK bootstrap..." -ForegroundColor Yellow
$bootstrapped = aws ssm get-parameter --name "/cdk-bootstrap/hnb659fds/version" --region $REGION --query "Parameter.Value" --output text 2>$null
if ($bootstrapped) {
    Write-Host "Bootstrap: OK (version $bootstrapped)" -ForegroundColor Green
} else {
    Write-Host "Bootstrap: Not found. Running bootstrap..." -ForegroundColor Yellow
    cdk bootstrap "aws://$ACCOUNT/$REGION" --toolkit-stack-name CDKToolkit
    Write-Host "Bootstrap: Done" -ForegroundColor Green
}

# Check asset bucket
Write-Host "`n[4] Checking asset bucket..." -ForegroundColor Yellow
$cdkJson = Get-Content "cdk.json" | ConvertFrom-Json
$assetBucket = $cdkJson.context.asset_bucket
if (-not $assetBucket) { $assetBucket = "cloudage-resources" }
$bucketExists = aws s3 ls "s3://$assetBucket" 2>$null
if ($bucketExists) {
    Write-Host "Asset bucket: s3://$assetBucket" -ForegroundColor Green
} else {
    Write-Host "Asset bucket not found. Skipping." -ForegroundColor Yellow
}

# Check layer zip
Write-Host "`n[5] Checking Lambda layer..." -ForegroundColor Yellow
if (Test-Path "requests_layer3_11.zip") {
    Write-Host "Layer zip: Found" -ForegroundColor Green
} else {
    Write-Host "Layer zip: NOT FOUND" -ForegroundColor Red
}

Write-Host "`n[6] Synthesizing stacks..." -ForegroundColor Yellow
cdk synth --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "Synth: OK" -ForegroundColor Green
} else {
    Write-Host "Synth: FAILED" -ForegroundColor Red
    exit 1
}

Write-Host "`n[7] Deploying stacks..." -ForegroundColor Yellow
$STACKS = @("APIStack", "IntegrationStack", "RekognitionStack", "VisualizationStack")
foreach ($stack in $STACKS) {
    Write-Host "  Deploying $stack..." -ForegroundColor Cyan
    cdk deploy $stack --require-approval never --outputs-file "cdk-outputs-$stack.json"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ${stack}: OK" -ForegroundColor Green
    } else {
        Write-Host "  ${stack}: FAILED" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n[8] Starting Glue crawler..." -ForegroundColor Yellow
aws glue start-crawler --name dynamodb-classifications-crawler --region $REGION 2>$null
Write-Host "Crawler started" -ForegroundColor Green

Write-Host "`n[DONE] All stacks deployed successfully!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Green
Write-Host "  1. Wait ~2 minutes for Glue crawler"
Write-Host "  2. Seed test data: python scan_classifications.py --seed --region $REGION"
Write-Host "  3. Open QuickSight: https://$REGION.quicksight.aws.amazon.com/" -ForegroundColor Cyan
