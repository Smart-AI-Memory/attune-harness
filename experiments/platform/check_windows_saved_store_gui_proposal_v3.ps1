# SOURCE REVIEW ONLY. Read/parse/compile data; do not invoke either proposal.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Proposal,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedProposalSha256,
    [Parameter(Mandatory=$true)][string]$GuiHelper,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedHelperSha256
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion -lt [version]'7.2') { throw 'Use fresh PowerShell 7.2+ for in-memory compilation.' }
$records = [Collections.Generic.List[object]]::new()
$inputs = @(
    @{ path = $Proposal; hash = $ExpectedProposalSha256; types = @('T2StandardProcess', 'T2GuiLeaseController') },
    @{ path = $GuiHelper; hash = $ExpectedHelperSha256; types = @('T2PrivateGuiLease') }
)
foreach ($inputRecord in $inputs) {
    if (-not [IO.Path]::IsPathRooted($inputRecord.path)) { throw 'Use absolute reviewed source paths.' }
    $hash = (Get-FileHash -LiteralPath $inputRecord.path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($hash -cne $inputRecord.hash.ToLowerInvariant()) { throw 'Source differs from the reviewed hash.' }
    $tokens = $null; $errors = $null
    $ast = [Management.Automation.Language.Parser]::ParseFile($inputRecord.path, [ref]$tokens, [ref]$errors)
    if ($errors.Count) { throw ('Source failed parsing: ' + $errors[0].ErrorId + ' at line ' + $errors[0].Extent.StartLineNumber) }
    $nodes = @($ast.FindAll({ param($node)
        $node -is [Management.Automation.Language.CommandAst] -and $node.GetCommandName() -eq 'Add-Type'
    }, $true))
    if ($nodes.Count -ne $inputRecord.types.Count) { throw 'Refuse a different number of literal C# blocks.' }
    $sources = [Collections.Generic.List[object]]::new()
    for ($i = 0; $i -lt $nodes.Count; $i++) {
        $elements = $nodes[$i].CommandElements
        if ($elements.Count -ne 3 -or $elements[1] -isnot [Management.Automation.Language.CommandParameterAst] -or
            $elements[1].ParameterName -ne 'TypeDefinition' -or
            $elements[2] -isnot [Management.Automation.Language.StringConstantExpressionAst] -or
            $elements[2].StringConstantType.ToString() -ne 'SingleQuotedHereString') { throw 'Refuse executable/expandable C# extraction.' }
        $source = $elements[2].Value
        $typeName = $inputRecord.types[$i]
        if ($source -notmatch ('public (static |sealed )class ' + [regex]::Escape($typeName) + '\b') -or
            $source -match 'ModuleInitializer' -or $source -match ('static\s+' + [regex]::Escape($typeName) + '\s*\(')) { throw 'Refuse missing type or static/module initializer.' }
        if ($typeName -as [type]) { throw 'Start a fresh PowerShell process; a type already exists.' }
        $compiled = @(Microsoft.PowerShell.Utility\Add-Type -TypeDefinition $source -Language CSharp -PassThru -ErrorAction Stop)
        if (-not ($compiled | Where-Object { $_.FullName -ceq $typeName })) { throw 'Expected public helper type was not compiled.' }
        $bytes = [Text.Encoding]::UTF8.GetBytes($source)
        $sourceHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
        $sources.Add([ordered]@{ type = $typeName; csharp_sha256 = $sourceHash })
    }
    $records.Add([ordered]@{ source_leaf = [IO.Path]::GetFileName($inputRecord.path); sha256 = $hash; compiled = $sources })
}
[ordered]@{
    status = 'parse_and_compile_only_passed'; revision = 3
    powershell = $PSVersionTable.PSVersion.ToString(); sources = $records
    proposal_invoked = $false; helper_invoked = $false; native_methods_invoked = $false
    accounts_or_credentials_created = $false; gui_objects_created = $false
    processes_launched = $false; assembly_output_written = $false; fixture_execution_authorized = $false
} | ConvertTo-Json -Depth 8
