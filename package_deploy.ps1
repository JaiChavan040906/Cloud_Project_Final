# Automated Packaging Script for Hospital Event Simulation
# This script builds the React frontend, packages it into a ZIP, builds Lambda dependencies, and packages the Lambda deployable ZIP.

$ErrorActionPreference = "Stop"

Write-Host "=== Starting Hospital Event Simulation Packager ===" -ForegroundColor Cyan

# 1. Verify Prerequisites
Write-Host "`n[1/4] Verifying prerequisites..." -ForegroundColor Yellow
$commands = @("npm", "pip")
foreach ($cmd in $commands) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Error "Prerequisite '$cmd' is not installed or not in system PATH."
    }
}
Write-Host "Prerequisites verified!" -ForegroundColor Green

# 2. Build and Package Frontend
Write-Host "`n[2/4] Building and packaging frontend..." -ForegroundColor Yellow
$frontendDir = Join-Path $PSScriptRoot "frontend"
$distZip = Join-Path $PSScriptRoot "frontend-dist.zip"

# Clean old zip
if (Test-Path $distZip) {
    Remove-Item $distZip -Force
}

# Run frontend build
Push-Location $frontendDir
try {
    Write-Host "Running npm install..." -ForegroundColor Gray
    npm install
    Write-Host "Running npm run build..." -ForegroundColor Gray
    npm run build
}
finally {
    Pop-Location
}

# Check dist folder exists
$distFolder = Join-Path $frontendDir "dist"
if (-not (Test-Path $distFolder)) {
    Write-Error "Frontend build failed. 'frontend/dist' folder was not created."
}

# Compress frontend assets
Write-Host "Compressing frontend dist directory..." -ForegroundColor Gray
Compress-Archive -Path "$distFolder\*" -DestinationPath $distZip -Force
Write-Host "Frontend successfully packaged into: $distZip" -ForegroundColor Green

# 3. Build and Package Lambda
Write-Host "`n[3/4] Packaging Lambda deployment package..." -ForegroundColor Yellow
$lambdaDist = Join-Path $PSScriptRoot "lambda_dist"
$lambdaZip = Join-Path $PSScriptRoot "lambda-deploy.zip"

# Clean old dist folder and zip
if (Test-Path $lambdaDist) {
    Write-Host "Cleaning old lambda_dist folder..." -ForegroundColor Gray
    Remove-Item -Recurse -Force $lambdaDist
}
if (Test-Path $lambdaZip) {
    Remove-Item $lambdaZip -Force
}

# Create dist folder
New-Item -ItemType Directory -Path $lambdaDist | Out-Null

# Install pip packages (forcing Linux x86_64 binaries for Lambda compatibility)
Write-Host "Installing Lambda python dependencies (x86_64)..." -ForegroundColor Gray
$reqPath = Join-Path $PSScriptRoot "lambda\requirements.txt"
pip install --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.12 --implementation cp -r $reqPath -t $lambdaDist

# Download and merge arm64 (aarch64) psycopg-binary to ensure compatibility with arm64 Lambda functions
Write-Host "Downloading and merging Lambda python dependencies (arm64/aarch64) for maximum compatibility..." -ForegroundColor Gray
$tempArmDir = Join-Path $PSScriptRoot "temp_arm"
if (Test-Path $tempArmDir) { Remove-Item -Recurse -Force $tempArmDir }
New-Item -ItemType Directory -Path $tempArmDir | Out-Null
try {
    pip install --platform manylinux2014_aarch64 --only-binary=:all: --python-version 3.12 --implementation cp psycopg-binary -t $tempArmDir
    Copy-Item -Path "$tempArmDir\*" -Destination $lambdaDist -Recurse -Force
}
finally {
    if (Test-Path $tempArmDir) { Remove-Item -Recurse -Force $tempArmDir }
}

# Copy backend app & data code
Write-Host "Copying backend application files..." -ForegroundColor Gray
$appSrc = Join-Path $PSScriptRoot "app"
$dataSrc = Join-Path $PSScriptRoot "data"
$handlerSrc = Join-Path $PSScriptRoot "lambda\handler.py"

Copy-Item $handlerSrc (Join-Path $lambdaDist "handler.py")
xcopy /E /I /Q $appSrc (Join-Path $lambdaDist "app\")
xcopy /E /I /Q $dataSrc (Join-Path $lambdaDist "data\")

# Compress Lambda package
Write-Host "Compressing Lambda package..." -ForegroundColor Gray
Compress-Archive -Path "$lambdaDist\*" -DestinationPath $lambdaZip -Force

# Clean up build directory to save space
Write-Host "Cleaning up build directory..." -ForegroundColor Gray
Remove-Item -Recurse -Force $lambdaDist

Write-Host "Lambda successfully packaged into: $lambdaZip" -ForegroundColor Green

# 4. Success Summary
Write-Host "`n=== Packaging Complete ===" -ForegroundColor Cyan
Write-Host "Ready for upload:" -ForegroundColor Green
Write-Host "1. Frontend Zip: $distZip (Upload/Unzip to EC2)" -ForegroundColor White
Write-Host "2. Lambda Zip  : $lambdaZip (Upload via AWS Console)" -ForegroundColor White
