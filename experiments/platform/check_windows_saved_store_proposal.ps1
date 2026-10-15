# REVIEW ARTIFACT ONLY. Never dot-source or invoke the account fixture.
# Run this separate checker in a fresh PowerShell 7 process with -NoProfile.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Proposal,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedSha256
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion -lt [version]'7.2') { throw 'Use a fresh PowerShell 7.2+ process for in-memory compilation.' }
if (-not [IO.Path]::IsPathRooted($Proposal)) { throw 'Use the absolute reviewed proposal path.' }
$actualHash = (Get-FileHash -LiteralPath $Proposal -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualHash -ne $ExpectedSha256.ToLowerInvariant()) { throw 'Proposal differs from the separately reviewed SHA-256.' }

# ParseFile reads syntax; it does not execute, dot-source, bind the fixture's
# parameters, invoke its switch route, or convert its AST into a ScriptBlock.
$tokens = $null
$errors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($Proposal, [ref]$tokens, [ref]$errors)
if ($errors.Count) {
    $errors | ForEach-Object { Write-Error ('Parse error: ' + $_.ErrorId + ' at line ' + $_.Extent.StartLineNumber) }
    throw 'Proposal failed PowerShell parsing.'
}
$addTypeNodes = @($ast.FindAll({
    param($node)
    $node -is [Management.Automation.Language.CommandAst] -and $node.GetCommandName() -eq 'Add-Type'
}, $true))
if ($addTypeNodes.Count -ne 1) { throw 'Expected exactly one reviewed Add-Type definition.' }
$elements = $addTypeNodes[0].CommandElements
if ($elements.Count -ne 3 -or
    $elements[1] -isnot [Management.Automation.Language.CommandParameterAst] -or
    $elements[1].ParameterName -ne 'TypeDefinition' -or
    $elements[2] -isnot [Management.Automation.Language.StringConstantExpressionAst] -or
    $elements[2].StringConstantType.ToString() -ne 'SingleQuotedHereString') {
    throw 'Refuse executable or expandable C# extraction.'
}
$source = $elements[2].Value
if ($source -notmatch 'public static class T2StandardProcess' -or
    $source -match 'ModuleInitializer' -or
    $source -match 'static\s+T2StandardProcess\s*\(') {
    throw 'Reviewed helper must have no module or static type initializer.'
}
if ('T2StandardProcess' -as [type]) { throw 'Start a fresh PowerShell process: the type already exists.' }

# Add-Type generates only an in-memory assembly. There is no OutputAssembly,
# constructor, method, property or P/Invoke invocation. The reviewed source has
# only method-level native calls and no static/module initialization code.
$types = @(Microsoft.PowerShell.Utility\Add-Type -TypeDefinition $source -Language CSharp -PassThru -ErrorAction Stop)
if (-not ($types | Where-Object { $_.FullName -eq 'T2StandardProcess' })) { throw 'Expected helper type was not compiled.' }
[ordered]@{
    status = 'parse_and_compile_only_passed'
    proposal_sha256 = $actualHash
    powershell = $PSVersionTable.PSVersion.ToString()
    account_fixture_invoked = $false
    native_helper_invoked = $false
    accounts_or_credentials_created = $false
    gui_security_objects_created = $false
    other_identity_launched = $false
    assembly_output_written = $false
    fixture_execution_authorized = $false
} | ConvertTo-Json
