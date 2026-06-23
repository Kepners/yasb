# Kill LFStatusBar, rebuild, deploy, restart
Write-Host "Stopping LFStatusBar..."
Get-Process -Name "*LFStatus*" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Build
Write-Host "Building yasb..."
Set-Location "C:\Users\kepne\OneDrive\Documents\GitHub\yasb\src"
& "../.venv/Scripts/python.exe" build.py build 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "BUILD SUCCESS"

    # Deploy library.zip to Program Files
    Write-Host "Deploying library.zip..."
    $src = "C:\Users\kepne\OneDrive\Documents\GitHub\yasb\src\dist\lib\library.zip"
    $dst = "C:\Program Files\yasb\lib\library.zip"

    if (Test-Path $src) {
        Copy-Item $src $dst -Force -ErrorAction SilentlyContinue
        if ($?) {
            Write-Host "Deployed to Program Files"
        } else {
            Write-Host "Need elevation for deploy - trying..."
            Start-Process powershell -Verb RunAs -ArgumentList "-Command", "Copy-Item '$src' '$dst' -Force" -Wait
        }
    }

    # Clear systray state
    Get-ChildItem "$env:LOCALAPPDATA\YASB\systray_state_*.json" -ErrorAction SilentlyContinue | Remove-Item -Force

    # Restart from dist
    Write-Host "Starting LFStatusBar..."
    Start-Process "C:\Users\kepne\OneDrive\Documents\GitHub\yasb\src\dist\LFStatusBar.exe" -WindowStyle Hidden
    Start-Sleep -Seconds 3
    Get-Process -Name "*LFStatus*" -ErrorAction SilentlyContinue | Format-Table Id, ProcessName
} else {
    Write-Host "BUILD FAILED"
}
