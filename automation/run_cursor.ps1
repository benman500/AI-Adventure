param(
    [Parameter(Mandatory = $true)]
    [string]$PromptFile
)

$PromptText = Get-Content $PromptFile -Raw

# Check which executable exists.
$AgentCommand = $null

if (Get-Command agent -ErrorAction SilentlyContinue) {
    $AgentCommand = "agent"
}
elseif (Get-Command cursor-agent -ErrorAction SilentlyContinue) {
    $AgentCommand = "cursor-agent"
}
else {
    Write-Error "Cursor CLI was not found. Install it and confirm that 'agent' or 'cursor-agent' works."
    exit 1
}

Write-Host "Starting Cursor CLI with $AgentCommand"

# IMPORTANT:
# Confirm the current headless syntax using:
#     agent --help
# or:
#     cursor-agent --help
#
# Cursor CLI versions may expose slightly different parameter names.
#
# The commonly documented pattern uses a print/headless prompt mode.
# Replace the next line if your CLI help displays different syntax.

& $AgentCommand -p $PromptText --output-format text

exit $LASTEXITCODE
