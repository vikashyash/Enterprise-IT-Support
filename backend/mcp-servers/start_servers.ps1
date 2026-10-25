# Starts the four MCP servers, each in its own PowerShell window. Run from any folder: .\start_servers.ps1
$serverModules = @("itsm.server", "device.server", "infrastructure.server", "iam.server")

foreach ($serverModule in $serverModules) {
    Start-Process powershell -WorkingDirectory $PSScriptRoot -ArgumentList "-NoExit", "-Command", "py -3.13 -m $serverModule"
}

# 