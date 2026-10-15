# Pure Windows path-syntax regressions against the actual reviewed C# method.
# Compile literal block only; invoke CanonicalPath by reflection, never Open,
# Close, file methods, process launch, GUI, account or credential code.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Proposal,
    [Parameter(Mandatory=$true)][string]$ExpectedSha256
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'These lexical tests require Windows Path semantics.' }
if ((Get-FileHash -LiteralPath $Proposal -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ExpectedSha256) { throw 'Refuse different source.' }
$tokens = $null; $errors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($Proposal, [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw 'Refuse invalid proposal syntax.' }
$nodes = @($ast.FindAll({ param($node)
    $node -is [Management.Automation.Language.CommandAst] -and $node.GetCommandName() -eq 'Add-Type'
}, $true))
if ($nodes.Count -ne 2) { throw 'Refuse different literal source count.' }
$elements = $nodes[1].CommandElements
if ($elements.Count -ne 3 -or $elements[2] -isnot [Management.Automation.Language.StringConstantExpressionAst] -or
    $elements[2].StringConstantType.ToString() -ne 'SingleQuotedHereString') { throw 'Refuse executable extraction.' }
$source = $elements[2].Value
if ($source -match 'ModuleInitializer' -or $source -match 'static\s+T2GuiLeaseController\s*\(') { throw 'Refuse type/module initialization.' }
if ('T2GuiLeaseController' -as [type]) { throw 'Start a fresh PowerShell process.' }
$null = Microsoft.PowerShell.Utility\Add-Type -TypeDefinition $source -Language CSharp -ErrorAction Stop
$method = [T2GuiLeaseController].GetMethod('CanonicalPath', [Reflection.BindingFlags]'Static,NonPublic')
if (-not $method) { throw 'Expected exact lexical method is missing.' }
$checks = [Collections.Generic.List[string]]::new()
foreach ($path in @('C:\ProgramData\AttuneT2Proof-0123\gui-helper.ps1', 'D:\a\attune-harness\gui control 雪\gui-helper.ps1')) {
    if ($method.Invoke($null, [object[]]@($path)) -cne $path) { throw 'A canonical fixture path changed.' }
    $checks.Add('accepted:' + $path)
}
$bad = @{
    relative = 'gui-helper.ps1'
    drive_relative = 'C:gui-helper.ps1'
    root_relative = '\gui-helper.ps1'
    unc = '\\server\share\gui-helper.ps1'
    extended_device = '\\?\C:\gui-helper.ps1'
    win32_device = '\\.\C:\gui-helper.ps1'
    parent_segment = 'C:\proof\..\gui-helper.ps1'
    current_segment = 'C:\proof\.\gui-helper.ps1'
    alternate_stream = 'C:\proof\gui-helper.ps1:extra'
    trailing_space = 'C:\proof \gui-helper.ps1'
    trailing_dot = 'C:\proof.\gui-helper.ps1'
    empty_component = 'C:\proof\\gui-helper.ps1'
    reserved_console = 'C:\proof\CON.ps1'
    reserved_port = 'C:\proof\COM1.ps1'
    wildcard = 'C:\proof\gui*.ps1'
    quote = 'C:\proof\gui".ps1'
    control_character = ('C:\proof\gui' + [char]1 + '.ps1')
    too_deep = ('C:\' + ((1..33 | ForEach-Object { 'part' }) -join '\') + '\gui-helper.ps1')
    too_long = ('C:\proof\' + ('x' * 1024) + '.ps1')
}
foreach ($name in @($bad.Keys | Sort-Object)) {
    $refused = $false
    try { $null = $method.Invoke($null, [object[]]@($bad[$name])) }
    catch {
        $cause = $_.Exception
        while ($cause.InnerException) { $cause = $cause.InnerException }
        if ($cause -is [ArgumentException]) { $refused = $true }
        else { throw }
    }
    if (-not $refused) { throw ('Expected lexical refusal: ' + $name) }
    $checks.Add('refused:' + $name)
}
[ordered]@{
    status = 'pure_path_syntax_passed'; count = $checks.Count; checks = $checks
    native_methods_invoked = $false; files_opened_by_controller_helper = $false
    handles_or_acl_or_launch_qualified = $false; accounts_or_credentials_created = $false
} | ConvertTo-Json -Depth 4
