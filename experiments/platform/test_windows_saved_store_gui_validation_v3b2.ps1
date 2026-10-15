# PURE RECORD REGRESSIONS ONLY. Extract only hash-reviewed validation functions.
# Never dot-source or invoke the account fixture, GUI helper or native methods.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Proposal,
    [Parameter(Mandatory=$true)][string]$ExpectedSha256
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ((Get-FileHash -LiteralPath $Proposal -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ExpectedSha256) { throw 'Refuse different source.' }
$tokens = $null; $errors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($Proposal, [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw 'Refuse invalid source syntax.' }
foreach ($name in @('Assert-T2ExactKeys', 'Assert-T2Integer', 'Assert-T2Problem', 'Assert-T2GuiRecord', 'Assert-GuiReady')) {
    $nodes = @($ast.FindAll({ param($node)
        $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name
    }, $true))
    if ($nodes.Count -ne 1) { throw 'Refuse missing/duplicate pure validation function.' }
    . ([scriptblock]::Create($nodes[0].Extent.Text))
}
$testNonce = '0123456789abcdef0123456789abcdef'
$testSid = 'S-1-5-21-1-2-3-1001'
function New-Record {
    return @{
        revision = [long]3; nonce = $testNonce; state = 'ready'; process_sid = $testSid
        station = ('AttuneT2-' + $testNonce); desktop = 'proof'; pid = [long]1234; failure = $null
        gui = @{
            MainThreadId = [long]11; SetupThreadId = [long]12
            SetupThreadExited = $true; HelperStationRestored = $true; HelperThreadDesktopUnchanged = $true
            Ready = $true; DesktopClosed = $false; StationClosed = $false; DescriptorFreed = $false
            PrimaryFailure = $null; TeardownFailures = @()
        }
    }
}
$checks = [Collections.Generic.List[string]]::new()
$value = New-Record
Assert-T2GuiRecord $value $testNonce $testSid 1234
Assert-GuiReady $value
$checks.Add('ready_valid')
$value.state = 'stopped'; $value.gui.Ready = $false
$value.gui.DesktopClosed = $true; $value.gui.StationClosed = $true; $value.gui.DescriptorFreed = $true
Assert-T2GuiRecord $value $testNonce $testSid 1234
$checks.Add('stopped_valid')
$cases = @{
    wrong_nonce = { param($v) $v.nonce = 'changed' }
    wrong_sid = { param($v) $v.process_sid = 'S-1-5-18' }
    wrong_pid = { param($v) $v.pid = [long]4321 }
    float_pid = { param($v) $v.pid = 1234.0 }
    boolean_revision = { param($v) $v.revision = $true }
    extra_field = { param($v) $v['unknown'] = 'value' }
    extra_gui_field = { param($v) $v.gui['unknown'] = $false }
    missing_gui_field = { param($v) $v.gui.Remove('HelperStationRestored') }
    string_joined = { param($v) $v.gui.SetupThreadExited = 'true' }
    setup_not_joined = { param($v) $v.gui.SetupThreadExited = $false }
    setup_same_thread = { param($v) $v.gui.SetupThreadId = [long]11 }
    station_not_restored = { param($v) $v.gui.HelperStationRestored = $false }
    desktop_changed = { param($v) $v.gui.HelperThreadDesktopUnchanged = $false }
    desktop_closed_early = { param($v) $v.gui.DesktopClosed = $true }
    failure_hidden_in_ready = { param($v) $v.failure = @{ stage = 'gui_lease'; type = 'TimeoutException' } }
    native_failure_hidden = { param($v) $v.gui.PrimaryFailure = @{ Stage = 'gui_setup'; Type = 'NativeFailure'; NativeCode = [long]170 } }
    teardown_failure_hidden = { param($v) $v.gui.TeardownFailures = @(@{ Stage = 'close_private_desktop'; Type = 'NativeFailure'; NativeCode = [long]170 }) }
    ready_false = { param($v) $v.gui.Ready = $false }
    unknown_state = { param($v) $v.state = 'success' }
    incomplete_stop = { param($v) $v.state = 'stopped'; $v.gui.Ready = $false }
}
foreach ($name in @($cases.Keys | Sort-Object)) {
    $value = New-Record
    & $cases[$name] $value | Out-Null
    $refused = $false
    try { Assert-T2GuiRecord $value $testNonce $testSid 1234 } catch { $refused = $true }
    if (-not $refused) { throw ('Expected refusal: ' + $name) }
    $checks.Add($name)
}
$value = New-Record
$value.state = 'failed'; $value.failure = @{ stage = 'gui_lease'; type = 'TimeoutException' }
Assert-T2GuiRecord $value $testNonce $testSid 1234 # Retain failed observation as data.
$refused = $false
try { Assert-GuiReady $value } catch { $refused = $true }
if (-not $refused) { throw 'A failed helper must not authorize proof launch.' }
$checks.Add('failed_observation_never_ready')

# A normal PowerShell hashtable is case-insensitive, so merely assigning Nonce
# can preserve the original nonce key and fail to construct a regression input.
# Use ordinal IDictionary objects, remove the exact old spelling, add its
# case-only mutation, and prove that spelling survived before validating it.
function Copy-OrdinalDictionary([Collections.IDictionary]$source) {
    $copy = [Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
    foreach ($key in $source.Keys) { $copy.Add([string]$key, $source[$key]) }
    return ,$copy
}
$caseSpecs = @(
    @{ name = 'case_only_top_nonce'; scope = 'top'; old = 'nonce'; mutated = 'Nonce'; keys = @('revision', 'nonce', 'state', 'process_sid', 'station', 'desktop', 'pid', 'gui', 'failure') },
    @{ name = 'case_only_gui_thread'; scope = 'gui'; old = 'MainThreadId'; mutated = 'mainThreadId'; keys = @('MainThreadId', 'SetupThreadId', 'SetupThreadExited', 'HelperStationRestored', 'HelperThreadDesktopUnchanged', 'Ready', 'DesktopClosed', 'StationClosed', 'DescriptorFreed', 'PrimaryFailure', 'TeardownFailures') },
    @{ name = 'case_only_problem_code'; scope = 'problem'; old = 'NativeCode'; mutated = 'nativeCode'; keys = @('Stage', 'Type', 'NativeCode') }
)
$caseFailures = [Collections.Generic.List[string]]::new()
$legacyAccepted = 0
foreach ($spec in $caseSpecs) {
    $record = New-Record
    if ($spec.scope -ceq 'top') { $map = Copy-OrdinalDictionary $record }
    elseif ($spec.scope -ceq 'gui') { $map = Copy-OrdinalDictionary $record.gui }
    else { $map = Copy-OrdinalDictionary @{ Stage = 'gui_setup'; Type = 'NativeFailure'; NativeCode = [long]170 } }
    if ($map -isnot [Collections.IDictionary]) { throw 'The case regression did not construct an IDictionary.' }
    Assert-T2ExactKeys $map $spec.keys # A valid ordinal dictionary must pass.
    $held = $map[$spec.old]
    if (-not $map.Remove($spec.old)) { throw 'The exact original key was missing.' }
    $map.Add($spec.mutated, $held)
    if ($map.Count -ne $spec.keys.Count -or @($map.Keys) -ccontains $spec.old -or
        @($map.Keys) -cnotcontains $spec.mutated) { throw 'The case-only mutation was erased or changed the schema size.' }
    # The precise default Compare-Object expression used by v3b1 must accept
    # this input. This guards the causal regression input; it does not invoke
    # old native code or claim that the whole legacy fixture was executed.
    if (@(Compare-Object @($map.Keys | Sort-Object) @($spec.keys | Sort-Object)).Count -ne 0) { throw 'The input does not expose the legacy case-insensitive comparison.' }
    $legacyAccepted++
    $exactRefused = $false
    try { Assert-T2ExactKeys $map $spec.keys } catch { $exactRefused = $true }
    if (-not $exactRefused) { $caseFailures.Add($spec.name + ':exact_keys_accepted') }
    $ownerRefused = $false
    try {
        if ($spec.scope -ceq 'top') { Assert-T2GuiRecord $map $testNonce $testSid 1234 }
        elseif ($spec.scope -ceq 'gui') { $record.gui = $map; Assert-T2GuiRecord $record $testNonce $testSid 1234 }
        else { Assert-T2Problem $map }
    } catch { $ownerRefused = $true }
    if (-not $ownerRefused) { $caseFailures.Add($spec.name + ':owner_accepted') }
    $checks.Add($spec.name)
}
if ($caseFailures.Count -ne 0) {
    [ordered]@{ status = 'case_key_regression_failed'; failures = $caseFailures; legacy_default_comparison_accepts = $legacyAccepted
        native_invoked = $false; fixture_invoked = $false; accounts_or_credentials_created = $false } | ConvertTo-Json -Depth 4 | Write-Output
    throw 'Case-only dictionary keys were accepted by a reviewed owner.'
}
if ($checks.Count -ne 26 -or $legacyAccepted -ne 3) { throw 'Expected all 23 original cases and 3 case-only regressions.' }
[ordered]@{ status = 'pure_validation_passed'; checks = $checks; count = $checks.Count; case_only_negative_cases = 3; legacy_default_comparison_accepts = $legacyAccepted
    native_invoked = $false; fixture_invoked = $false; accounts_or_credentials_created = $false } | ConvertTo-Json -Depth 4
