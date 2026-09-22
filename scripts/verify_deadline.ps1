$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host '== Backend regression suite ==' -ForegroundColor Cyan
python -m pytest tests -q

Write-Host '== Fixture governance ==' -ForegroundColor Cyan
python tests/fixtures/validate_ai_fixtures.py
python tests/fixtures/validate_review_fixtures.py

Write-Host '== Frontend dependencies ==' -ForegroundColor Cyan
Set-Location (Join-Path $RepoRoot 'frontend')
npm install

Write-Host '== Frontend component/integration tests ==' -ForegroundColor Cyan
npm run test

Write-Host '== Frontend production build ==' -ForegroundColor Cyan
npm run build

Write-Host '== OpenAPI / TypeScript contract synchronization ==' -ForegroundColor Cyan
Set-Location $RepoRoot
python scripts/verify_contracts.py

Write-Host '== Evaluation bundle immutability ==' -ForegroundColor Cyan
$bundleDiff = git diff --name-only origin/main -- sdoc-hackathon-bundle/
if ($bundleDiff) {
    Write-Host 'FAILED: sdoc-hackathon-bundle has modifications:' -ForegroundColor Red
    Write-Host $bundleDiff
    exit 1
}

Write-Host ''
Write-Host 'ALL DEADLINE VERIFICATION CHECKS PASSED.' -ForegroundColor Green
Write-Host 'The frontend production build is in docs/ and docs/reference/ui_prototype.html remains the preserved prototype.'
