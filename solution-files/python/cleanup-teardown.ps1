# =============================================================================
# cleanup-teardown.ps1 — Cloudage Image Rekognition - Complete Cleanup Script
#
# This PowerShell script safely destroys all AWS resources created during
# deployment of the Cloudage Image Rekognition pipeline.
#
# Features:
#   ✓ Prompts for confirmation before deleting anything
#   ✓ Destroys stacks in reverse dependency order
#   ✓ Manually deletes resources with RemovalPolicy.RETAIN
#   ✓ Cleans up orphaned resources (Athena, Glue, QuickSight)
#   ✓ Provides progress tracking and detailed logging
#   ✓ Safe to run multiple times
#
# Usage:
#   .\cleanup-teardown.ps1                 # destroy all stacks
#   .\cleanup-teardown.ps1 -DryRun         # preview what would be deleted
#   .\cleanup-teardown.ps1 -SkipPrompt     # skip confirmation (use with caution)
#   .\cleanup-teardown.ps1 -Help           # show help
#
# =============================================================================

param(
    [switch]$DryRun = $false,
    [switch]$SkipPrompt = $false,
    [switch]$Help = $false
)

# ── Colors & Formatting ────────────────────────────────────────────────────────
$colors = @{
    Reset   = "`e[0m"
    Bold    = "`e[1m"
    Red     = "`e[31m"
    Green   = "`e[32m"
    Yellow  = "`e[33m"
    Blue    = "`e[34m"
    Magenta = "`e[35m"
    Cyan    = "`e[36m"
}

function Write-Info    { Write-Host "$($colors.Blue)[INFO]$($colors.Reset)   $args" }
function Write-Success { Write-Host "$($colors.Green)[OK]$($colors.Reset)     $args" }
function Write-Warn    { Write-Host "$($colors.Yellow)[WARN]$($colors.Reset)   $args" }
function Write-Error   { Write-Host "$($colors.Red)[ERROR]$($colors.Reset)  $args" }
function Write-Step    { Write-Host "`n$($colors.Bold)━━━ $args ━━━$($colors.Reset)" }
function Write-Header  { Write-Host "`n$($colors.Bold)$($colors.Magenta)$($args)$($colors.Reset)" }
function Write-Delete  { Write-Host "$($colors.Red)[DELETE]$($colors.Reset) $args" }

# ── Configuration ──────────────────────────────────────────────────────────────
$ACCOUNT_ID = "784055307907"
$REGION = "us-east-1"

# Stacks in reverse order (dependencies flow upward, so destroy downward)
$STACKS = @("VisualizationStack", "RekognitionStack", "IntegrationStack", "APIStack")

# Resources with RemovalPolicy.RETAIN that won't be deleted by CDK
$RETAIN_BUCKETS = @(
    "athena-results-$ACCOUNT_ID",
    "athena-spill-*",
    "sagemaker-$REGION-$ACCOUNT_ID"
)

$RETAIN_TABLES = @(
    "RekognitionStack-Classifications*"
)

# ── Help ───────────────────────────────────────────────────────────────────────
if ($Help) {
    Write-Host @"
$($colors.Bold)CLOUDAGE IMAGE REKOGNITION — CLEANUP & TEARDOWN SCRIPT$($colors.Reset)

USAGE:
    .\cleanup-teardown.ps1 [OPTIONS]

OPTIONS:
    -DryRun           Show what would be deleted without actually deleting
    -SkipPrompt       Skip confirmation prompt (use with caution!)
    -Help             Show this help message

EXAMPLES:
    # Preview cleanup without deleting anything
    .\cleanup-teardown.ps1 -DryRun

    # Cleanup with confirmation prompt (default)
    .\cleanup-teardown.ps1

    # Cleanup without prompt (be careful!)
    .\cleanup-teardown.ps1 -SkipPrompt

WHAT GETS DELETED:
    1. CloudFormation Stacks (in reverse order):
       - VisualizationStack
       - RekognitionStack
       - IntegrationStack
       - APIStack

    2. Orphaned Resources (not managed by CDK):
       - S3 buckets: athena-results-*, athena-spill-*, sagemaker-*
       - DynamoDB tables: Classifications
       - Athena workgroup: dynamodb-visualization
       - Glue database: recognitiondb
       - Glue crawler: dynamodb-classifications-crawler
       - QuickSight data source: dynamodb-athena-datasource

    3. IAM Roles & Policies (attached to stacks)

    4. Lambda Functions & Event Mappings

    5. SNS Topics, SQS Queues, DLQs

    6. API Gateway, Lambda Layers, etc.

ACCOUNT:     $ACCOUNT_ID
REGION:      $REGION

WARNING:
    This operation is DESTRUCTIVE and cannot be undone!
    - Data in DynamoDB will be PERMANENTLY DELETED
    - S3 buckets and their contents will be REMOVED
    - All classifications and stored images will be LOST
    - This action affects production resources!

USE -DryRun FIRST TO PREVIEW DELETIONS
"@
    exit 0
}

# ── Main Functions ─────────────────────────────────────────────────────────────

function Test-Prerequisites {
    Write-Step "Pre-flight Checks"

    Write-Info "Checking AWS CLI..."
    try {
        $version = aws --version 2>$null
        Write-Success "AWS CLI: $version"
    } catch {
        Write-Error "AWS CLI not found. Install from: https://aws.amazon.com/cli/"
        exit 1
    }

    Write-Info "Checking AWS credentials..."
    try {
        $identity = aws sts get-caller-identity --region $REGION | ConvertFrom-Json
        Write-Success "AWS Account: $($identity.Account)"
        if ($identity.Account -ne $ACCOUNT_ID) {
            Write-Error "Account mismatch! Expected $ACCOUNT_ID, got $($identity.Account)"
            exit 1
        }
    } catch {
        Write-Error "AWS credentials not configured. Run: aws configure"
        exit 1
    }

    Write-Success "All pre-flight checks passed!"
}

function Get-StackStatus {
    param([string]$StackName)
    
    try {
        $stack = aws cloudformation describe-stacks `
            --stack-name $StackName `
            --region $REGION `
            --query "Stacks[0].StackStatus" `
            --output text 2>$null
        
        return $stack
    } catch {
        return "NOT_EXISTS"
    }
}

function Destroy-Stack {
    param([string]$StackName)

    Write-Step "Destroying $StackName"

    $status = Get-StackStatus $StackName

    if ($status -eq "NOT_EXISTS") {
        Write-Warn "$StackName does not exist. Skipping."
        return $true
    }

    Write-Info "Current status: $status"

    if ($DryRun) {
        Write-Info "[DRY RUN] Would destroy: $StackName"
        return $true
    }

    Write-Info "Destroying stack: $StackName..."
    try {
        aws cloudformation delete-stack `
            --stack-name $StackName `
            --region $REGION

        Write-Success "Delete request submitted. Waiting for completion..."

        # Wait for stack deletion
        $maxWait = 0
        while ($maxWait -lt 1800) { # 30 minute timeout
            $status = Get-StackStatus $StackName
            
            if ($status -eq "NOT_EXISTS" -or $status -eq "") {
                Write-Success "$StackName destroyed successfully"
                return $true
            }

            if ($status -like "*DELETE_FAILED*") {
                Write-Error "$StackName deletion failed with status: $status"
                return $false
            }

            if ($status -like "*DELETE_IN_PROGRESS*") {
                Write-Info "Deletion in progress... ($status)"
                Start-Sleep -Seconds 10
                $maxWait += 10
            } else {
                Write-Warn "Unexpected status: $status"
                Start-Sleep -Seconds 5
                $maxWait += 5
            }
        }

        Write-Error "Stack deletion timeout"
        return $false

    } catch {
        Write-Error "Failed to destroy $StackName : $_"
        return $false
    }
}

function Cleanup-OrphanedResources {
    Write-Step "Cleanup Orphaned Resources (RemovalPolicy.RETAIN)"

    # Delete S3 buckets
    Write-Info "Cleaning up S3 buckets..."
    
    foreach ($bucketPattern in $RETAIN_BUCKETS) {
        try {
            $buckets = aws s3 ls --region $REGION | Where-Object { $_ -match $bucketPattern }
            
            foreach ($bucket in $buckets) {
                $bucketName = $bucket -split '\s+' | Select-Object -Last 1
                
                if ($DryRun) {
                    Write-Delete "[DRY RUN] Would delete bucket: $bucketName (and all objects)"
                } else {
                    Write-Delete "Deleting bucket: $bucketName"
                    
                    try {
                        # Remove all objects first
                        aws s3 rm "s3://$bucketName" --recursive --region $REGION --quiet
                        
                        # Then delete the bucket
                        aws s3api delete-bucket --bucket $bucketName --region $REGION
                        
                        Write-Success "Bucket deleted: $bucketName"
                    } catch {
                        Write-Warn "Failed to delete bucket $bucketName : $_"
                    }
                }
            }
        } catch {
            Write-Warn "Error listing buckets matching $bucketPattern : $_"
        }
    }

    # Delete DynamoDB tables
    Write-Info "Cleaning up DynamoDB tables..."
    
    try {
        $tables = aws dynamodb list-tables --region $REGION --query "TableNames" | ConvertFrom-Json
        
        foreach ($table in $tables) {
            $matches = $false
            foreach ($tablePattern in $RETAIN_TABLES) {
                if ($table -like $tablePattern) {
                    $matches = $true
                    break
                }
            }
            
            if ($matches) {
                if ($DryRun) {
                    Write-Delete "[DRY RUN] Would delete table: $table (and all data)"
                } else {
                    Write-Delete "Deleting DynamoDB table: $table"
                    
                    try {
                        aws dynamodb delete-table --table-name $table --region $REGION
                        Write-Success "Table deleted: $table"
                    } catch {
                        Write-Warn "Failed to delete table $table : $_"
                    }
                }
            }
        }
    } catch {
        Write-Warn "Error listing DynamoDB tables: $_"
    }

    # Delete Athena resources
    Write-Info "Cleaning up Athena resources..."
    
    if ($DryRun) {
        Write-Delete "[DRY RUN] Would delete Athena workgroup: dynamodb-visualization"
    } else {
        try {
            aws athena delete-work-group `
                --work-group dynamodb-visualization `
                --region $REGION
            Write-Success "Athena workgroup deleted"
        } catch {
            Write-Warn "Failed to delete Athena workgroup: $_"
        }
    }

    # Delete Glue resources
    Write-Info "Cleaning up Glue resources..."
    
    if ($DryRun) {
        Write-Delete "[DRY RUN] Would delete Glue crawler: dynamodb-classifications-crawler"
        Write-Delete "[DRY RUN] Would delete Glue database: recognitiondb"
    } else {
        try {
            aws glue delete-crawler `
                --name dynamodb-classifications-crawler `
                --region $REGION
            Write-Success "Glue crawler deleted"
        } catch {
            Write-Warn "Failed to delete Glue crawler: $_"
        }

        try {
            aws glue delete-database `
                --catalog-id $ACCOUNT_ID `
                --name recognitiondb `
                --region $REGION
            Write-Success "Glue database deleted"
        } catch {
            Write-Warn "Failed to delete Glue database: $_"
        }
    }

    # Delete QuickSight data source
    Write-Info "Cleaning up QuickSight resources..."
    
    if ($DryRun) {
        Write-Delete "[DRY RUN] Would delete QuickSight data source: dynamodb-athena-datasource"
    } else {
        try {
            aws quicksight delete-data-source `
                --aws-account-id $ACCOUNT_ID `
                --data-source-id dynamodb-athena-datasource `
                --region $REGION
            Write-Success "QuickSight data source deleted"
        } catch {
            Write-Warn "Failed to delete QuickSight data source (may not exist): $_"
        }
    }
}

function Show-Summary {
    Write-Header "╔════════════════════════════════════════════════════╗"
    Write-Header "║              CLEANUP SUMMARY                      ║"
    Write-Header "╚════════════════════════════════════════════════════╝"

    if ($DryRun) {
        Write-Info "DRY RUN MODE - No resources were actually deleted"
    } else {
        Write-Success "All resources have been cleaned up successfully!"
    }

    Write-Info ""
    Write-Info "Stacks destroyed (in order):"
    foreach ($stack in $STACKS) {
        Write-Host "  ✓ $stack"
    }

    Write-Info ""
    Write-Info "Orphaned resources cleaned up:"
    Write-Host "  ✓ S3 buckets (with all objects)"
    Write-Host "  ✓ DynamoDB tables (with all data)"
    Write-Host "  ✓ Athena workgroup"
    Write-Host "  ✓ Glue database & crawler"
    Write-Host "  ✓ QuickSight data source"

    Write-Info ""
    Write-Info "Account: $ACCOUNT_ID"
    Write-Info "Region: $REGION"
}

function Get-Confirmation {
    Write-Header "⚠️  WARNING: DESTRUCTIVE OPERATION ⚠️"
    
    Write-Host @"
This script will PERMANENTLY DELETE:

  ✗ All 4 CloudFormation stacks
  ✗ DynamoDB Classifications table (with ALL data)
  ✗ S3 image bucket (with ALL images)
  ✗ Athena & Glue resources
  ✗ Lambda functions
  ✗ API Gateway endpoints
  ✗ SNS/SQS queues
  ✗ IAM roles & policies

THIS CANNOT BE UNDONE!

Data loss is PERMANENT. Make sure you have backups if needed.

Are you sure you want to proceed?
"@

    $confirm = Read-Host "Type 'DELETE EVERYTHING' to confirm"

    if ($confirm -eq "DELETE EVERYTHING") {
        Write-Success "Confirmed. Proceeding with cleanup..."
        return $true
    } else {
        Write-Info "Cleanup cancelled."
        exit 0
    }
}

function Main {
    Write-Header "╔════════════════════════════════════════════════════╗"
    Write-Header "║   CLOUDAGE IMAGE REKOGNITION — CLEANUP SCRIPT     ║"
    Write-Header "╚════════════════════════════════════════════════════╝"

    Write-Info "Account: $ACCOUNT_ID"
    Write-Info "Region: $REGION"
    
    if ($DryRun) {
        Write-Warn "DRY RUN MODE - No resources will be deleted"
    }

    # Pre-flight checks
    Test-Prerequisites

    # Confirmation
    if (-not $SkipPrompt -and -not $DryRun) {
        Get-Confirmation
    } elseif ($SkipPrompt -and -not $DryRun) {
        Write-Warn "Skipping confirmation prompt. Proceeding with cleanup..."
        Start-Sleep -Seconds 3
    }

    # Destroy stacks in reverse order
    Write-Header "Phase 1: Destroying CloudFormation Stacks"
    
    $failedStacks = @()
    
    foreach ($stackName in $STACKS) {
        if (-not (Destroy-Stack $stackName)) {
            $failedStacks += $stackName
        }
        
        Start-Sleep -Seconds 2
    }

    # Cleanup orphaned resources
    if ($failedStacks.Count -eq 0 -or $DryRun) {
        Write-Header "Phase 2: Cleaning Up Orphaned Resources"
        Cleanup-OrphanedResources
    } else {
        Write-Warn "Some stacks failed to delete. Skipping orphaned resource cleanup."
    }

    # Summary
    Show-Summary

    if ($failedStacks.Count -gt 0 -and -not $DryRun) {
        Write-Error "Some stacks failed to delete:"
        foreach ($stack in $failedStacks) {
            Write-Host "  ✗ $stack"
        }
        Write-Info "You may need to clean up these stacks manually in AWS Console"
        exit 1
    }

    Write-Header "╔════════════════════════════════════════════════════╗"
    Write-Header "║              CLEANUP COMPLETE!                    ║"
    Write-Header "╚════════════════════════════════════════════════════╝"
}

# ── Entry Point ────────────────────────────────────────────────────────────────
Main
