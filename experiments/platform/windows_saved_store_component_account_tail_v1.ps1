# PROPOSAL ONLY. Future workflow job must stay literalfalse until fresh approval.
# Called in SAME fresh process immediately after exact safe-preflight3 returned0.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Repo,
      [Parameter(Mandatory=$true)][string]$ControllerPython)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not ('T2BuildCaptureV1' -as [type]) -or $env:GITHUB_ACTIONS -cne 'true') { throw 'Require the reviewed same-process preflight in disposable CI.' }
$owned = Join-Path $env:RUNNER_TEMP 'saved-store-build-safe'
$controller = [Security.Principal.WindowsIdentity]::GetCurrent().User
$item = Get-Item -LiteralPath $owned -Force
$acl = Get-Acl -LiteralPath $owned
$rules = @($acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier]))
if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
    -not $acl.AreAccessRulesProtected -or $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -cne $controller.Value -or
    $rules.Count -ne 2 -or @($rules | Where-Object { $_.IdentityReference.Value -ceq $controller.Value }).Count -ne 1 -or @($rules | Where-Object { $_.IdentityReference.Value -ceq 'S-1-5-18' }).Count -ne 1 -or @($rules | Where-Object { $_.IdentityReference.Value -cnotin @($controller.Value,'S-1-5-18') -or $_.FileSystemRights -ne [Security.AccessControl.FileSystemRights]::FullControl -or $_.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow }).Count) { throw 'Private controller root changed.' }
$preflight = [IO.File]::ReadAllText((Join-Path $owned 'preflight.json')) | ConvertFrom-Json -AsHashtable
if ($preflight.status -cne 'safe_build_and_module_startup_completed' -or $preflight.failure_type -or $preflight.cold.cases.Count -ne 7 -or $preflight.startup.installed.rows.Count -ne 118) { throw 'Safe prerequisite incomplete.' }
$pinsJson = @'
{
  ".github/workflows/windows-saved-store-build-safe-preflight.yml": "4c89a816da8eadcb4358ec401134e5b8f4f5729071a1a6389ed323e8febe85d9",
  ".github/workflows/windows-saved-store-cold-preflight.yml": "04421de56c01d2bacf2402f91c629f375fd61c5f776e65372ff982ac8d1de662",
  ".github/workflows/windows-saved-store-platform-build-safe-preflight.yml": "99446d1716415b9ff3a971873c401f7b922da386b0fc305f4d5bc09ba2261b64",
  ".github/workflows/windows-saved-store-reviewed-execution.yml": "30e11a181edf79eecb0667686d2da540fe9c7047829dc31ddaa50e23d88dfc6e",
  "experiments/platform/.gitattributes": "e0f1a9aaa1a71b35b8ca8d5c59aff19031710a1239b16cd6a2afcc6096383698",
  "experiments/platform/check_windows_saved_store_account_inputs_v2.py": "7fc6169c570d65d4493d70443ca27cb643d9127d8a3c416ac7cd7636388eb6be",
  "experiments/platform/check_windows_saved_store_account_inputs_v3.py": "7874a4819f18bf77dc0287b3895b0b05cceedec06d9cf3252d99e00f5b63555c",
  "experiments/platform/check_windows_saved_store_merge_inputs_v1.py": "91d373245ace997eca32725ceea73f2131ef3ac1f39f5194f423f4cf15351559",
  "experiments/platform/project_windows_saved_store_build_v1.py": "3a3aa7a53cdb53b8421d6116bdd0160757967b3472e6a39052987971828f20d8",
  "experiments/platform/project_windows_saved_store_build_v2.py": "c8ca4eafe05f14028d6d930e81f0cf42fa4d90d5cb2582914c1468b75bf3e0d8",
  "experiments/platform/windows_saved_store_build_preflight_v1.ps1": "02a1475590060160c1209db3a8c98e63340e7e5be8680b7b6f945c0fda38f5a3",
  "experiments/platform/windows_saved_store_build_preflight_v2.ps1": "099cbf93ab82335b2debe89afec6813228c64fde0357f8b55451823ed3cb9fcf",
  "experiments/platform/windows_saved_store_build_preflight_v3.ps1": "9ecd7e5832cefe3e1feb54881e696b913aad43294720e59bbf7e13b7bbf40a9a",
  "experiments/platform/windows_saved_store_combined_driver_v1.py": "e3aa0931328aabd2541b64b21f717c478b8121278dc7d10bb597e0cb0cf41937",
  "experiments/platform/windows_saved_store_combined_driver_v2.py": "b61a452cb8f59862cee4a366510b74c73544d62e83dc4a81288e28b82e717ca0",
  "experiments/platform/windows_saved_store_combined_driver_v3.py": "7ceb7519b2df1cca15729e3b96b0c0eba91f86b26cab97cbafe82752ef347a09",
  "experiments/platform/windows_saved_store_component_adapter_v1.py": "a1cb9a2818b3a42f45ebb744fc890017f0f1a5f7129b47a4416b2ab7a0bfd9c3",
  "experiments/platform/windows_saved_store_component_route_v1.py": "2020c0aa0ce28f53ccafdb684d04982e8cb4ccef9de98475a61b7215a7aa3141",
  "experiments/platform/windows_saved_store_gui_lease_helper_v4.ps1": "5786e2eefbb6e61f65ef4caaf17a4668ad7dd14ae8f552d72dffcc21845729bf",
  "experiments/platform/windows_saved_store_helper_cold_compile_v1.ps1": "496275b061b807302281834e036546361b5a1aa3651a3553c553b23db4db6885",
  "experiments/platform/windows_saved_store_namespace_witness_v4.py": "f326803457453fccf02b795144ef1a48986c4c7068eef87aa56d21591ddd643e",
  "experiments/platform/windows_saved_store_proof.py": "b233497ffe18973eca3a4db29b2eca7ee5269c4ae2ef78429a8cf10db1ce7355",
  "experiments/platform/windows_saved_store_source_manifest_v2.json": "d6e80ebd18c19d5b17b35bfdd4c0dc521a24e1dbb0a18eeba14247fcd7e875d8",
  "experiments/platform/windows_saved_store_source_manifest_v3.json": "fcf8365fc00aeade30d8bdfa4c4f3e0f5ea869aabb1fbc1ce80466c3b999ae5a",
  "experiments/platform/windows_saved_store_source_manifest_v4.json": "6b33976fcc9e7c1bcf276f82c9d4e0ad1d795008a74fb3c4343d86a7573c430a",
  "experiments/platform/windows_saved_store_standard_user_gui_proposal_v3b3.ps1": "696879df5b141def393235708f3a2baf0e8c9bb1cdb24d125082b53bc81a5804",
  "requirements-mcp.lock": "50f956aff914ee8ca2e85e00e3cc35aa56fff07213b659d962d7c9d91be94735",
  "requirements-redis.lock": "84f43680576915e1e8716902d85acc6b2ae63a4451eb55f5eaddabbf9806c09c",
  "requirements-tokens.lock": "32fbeb94891432d45936d39b98513550e87405a278c3aaaabb714aa38c20de53",
  "requirements-voyage.lock": "6a2f18db82d16ec3e8c8da55b282a3f7627b9ae025fb7cb11d14b6f7b512e441",
  "requirements-workflow.lock": "60ba53cfeba53c784331a689f948c5cbd046ed20f4e84fd6023eacf0ff656fad",
  "tests/.gitattributes": "69778c577642ecd3fe7b8c329dff6948d7ccb7fd8afde301711b12e63ccdbf8d",
  "tests/fixtures/windows_saved_store_component_v1/inputs-bde.zip": "c0c4ec0f8c274ec0782bc19844bf7a5cbdb600c4cb678ea70e3ad8773d703fe4",
  "tests/fixtures/windows_saved_store_component_v1/protocol.zip": "c4d27a6c8f3ad50dbe08f8d181d958ed8c5bad4542f1bce1f8146e3cabe667bb",
  "tests/fixtures/windows_saved_store_component_v1/records.json": "c062a603a937a00a25d53bc266927c8c6f9c45ec705d27c4158a4960de5f4e1a",
  "tests/fixtures/windows_saved_store_component_v1/tree.txt": "4c7854c36eaefc8022295fe7fc71947fa4c31237287adc69c8b3c749070c8282",
  "tests/fixtures/windows_saved_store_ffc_campaign_v1.zip": "2aa85e0b712cd82a1776bd1a021c5dca9098007c8775bbbd68fded22afaefde3",
  "tests/fixtures/windows_saved_store_wheel_metadata_v1.json": "3c18bc5babed6aae2e4da8ce8549cdabe830c9b6233abc0ee571e30d9a73aa66",
  "tests/test_windows_saved_store_account_inputs_v2.py": "6fbe500f7bee3945a3e2817241b805464a9c8b127124b5b54fb6589843827382",
  "tests/test_windows_saved_store_build_preflight.py": "675b61fbd3ec45ccfb263320e581bf3ada47c30ce2b98745cf4f4c2f40d749c8",
  "tests/test_windows_saved_store_build_projection.py": "1bc16cf178c99a5ba6940849cb493ccac82c576578f6dc5c386193cb1db5e181",
  "tests/test_windows_saved_store_component_adapter.py": "3c517e7913e396b3bc383ea87660e76c8f80b815144b1aed72029b2c3cfad4dc",
  "tests/test_windows_saved_store_component_route.py": "d1b29998038ab737290d6cff6dbe91904ca85c26afa6eecb68068d54f02b0481",
  "tests/test_windows_saved_store_profile_workflow.py": "2cb8ed514264f95901b3f913cdb2f985e795db1bc19d22aa9826ba5e55f3c278",
  "tests/test_windows_saved_store_wheel_profiles.py": "4dcbe314d4180b0c0e9832d433e828a90d39fbeec65818fb588d838c75876b1f",
  "experiments/platform/windows_saved_store_anchor_setup_v1.py": "4111e1e27bf81095cc52f170d17d590e510d37e8e8779ad3a7a4b5a251513a57",
  "experiments/platform/windows_saved_store_standard_user_gui_proposal_v4.ps1": "0f8bc51e984dedd5cace1c6c93e5278dd24273b077fc8e39b98e8099baa276c8",
  "experiments/platform/windows_saved_store_ack_gate_v1.py": "5322b81ab10bf83634685a245b535d6e1d06ff1682a941101f10116564450651"
}
'@
$pins = $pinsJson | ConvertFrom-Json -AsHashtable
$gate = (Resolve-Path (Join-Path $Repo 'experiments/platform/windows_saved_store_ack_gate_v1.py')).Path
$fixture = (Resolve-Path (Join-Path $Repo 'experiments/platform/windows_saved_store_standard_user_gui_proposal_v4.ps1')).Path
$publisher = (Resolve-Path (Join-Path $Repo 'experiments/platform/windows_saved_store_anchor_setup_v1.py')).Path
$manifest = (Resolve-Path (Join-Path $owned 'protocol/manifest.json')).Path
$helper = (Resolve-Path (Join-Path $owned 'protocol/helper.ps1')).Path
$driver = (Resolve-Path (Join-Path $owned 'protocol/driver.py')).Path
$wheel = Join-Path $owned 'wheel/attune_harness-1.4.0-py3-none-any.whl'
$basePython = & $ControllerPython -I -c 'import sys; print(sys._base_executable)'
if ($LASTEXITCODE -ne 0) { throw 'Base interpreter query failed.' }
$fixtureCwd = Join-Path $owned 'account-fixture-cwd'
$evidence = Join-Path $owned 'account-fixture'
$entryPath = Join-Path $owned 'account-entry.json'
$callerPath = Join-Path $owned 'account-caller.json'
$gateOutput = Join-Path $owned 'account-ack-gate.json'
foreach ($path in @($Repo,$ControllerPython,$basePython,$owned,$gate,$fixture,$publisher,$manifest,$helper,$driver,$wheel,$fixtureCwd,$evidence,$entryPath,$callerPath,$gateOutput)) {
    if (-not [IO.Path]::IsPathFullyQualified($path)) { throw 'Require absolute inputs before moving cwd.' }
}
foreach ($path in @($fixtureCwd,$evidence,$entryPath,$callerPath,$gateOutput)) { if (Test-Path -LiteralPath $path) { throw 'Refuse retained account output/cwd.' } }
$caller = [ordered]@{ status='caller_started'; entry_completed=$false; fixture_invocation_attempted=$false; fixture_returned_normally=$false; failure_type=$null; wheel_sha256=$null; wheel_closed=$false; sources_closed=$false; close_failures=[Collections.Generic.List[string]]::new(); t2_d3_passed=$false; production_port_allowed=$false }
function Save-Caller { [IO.File]::WriteAllText($callerPath,($caller | ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false)) }
function Capture-Controller([string]$name,[string[]]$arguments) {
    $value = [T2BuildCaptureV1]::Run($ControllerPython,$arguments,(Get-Location).Path,30)
    [IO.File]::WriteAllText((Join-Path $owned ($name+'-capture.json')),($value | ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $owned ($name+'-stdout.txt')),$value.Stdout.Text,[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $owned ($name+'-stderr.txt')),$value.Stderr.Text,[Text.UTF8Encoding]::new($false))
    if (-not $value.Started -or -not $value.RootExitConfirmed -or -not $value.StreamsCompleted -or $value.TimedOut -or $value.KillTreeRequested -or $value.FailureType -or $value.Stdout.FailureType -or $value.Stderr.FailureType -or $value.Stdout.DiscardedCharacters -ne 0 -or $value.Stderr.DiscardedCharacters -ne 0 -or $value.ExitCode -ne 0) { throw 'Bounded controller child refused.' }
}
$entryCode = @'
import hashlib,json,pathlib,sys,types
source,repo,owned,pins,expected,output=sys.argv[1:]
raw=pathlib.Path(source).read_bytes()
if len(raw)>1048576 or hashlib.sha256(raw).hexdigest()!='5322b81ab10bf83634685a245b535d6e1d06ff1682a941101f10116564450651': raise ValueError('gate_source_refused')
m=types.ModuleType('t2_account_entry');m.__file__=source;exec(compile(raw,source,'exec'),m.__dict__)
report={'status':'entry_incomplete','accounts_or_credentials_created':False,'failure_type':None}
with pathlib.Path(output).open('x',encoding='ascii') as stream:
 def save(value):
  report.update(value);stream.seek(0);json.dump(report,stream,ensure_ascii=True,indent=2);stream.write('\n');stream.truncate();stream.flush()
 save({})
 try:save(m.admit(pathlib.Path(repo),pathlib.Path(owned),json.loads(pins),expected,save))
 except Exception as e:save({'status':'entry_refused','failure_type':type(e).__name__});sys.exit(1)
'@
$wheelLease = $null
$sourceLeases = [Collections.Generic.List[IO.FileStream]]::new()
Save-Caller
try {
    # One selected path/object; no later glob/reselection is used by the fixture.
    $wheelLease = [IO.File]::Open($wheel,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    $caller.wheel_sha256 = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($wheelLease)).ToLowerInvariant()
    if ($caller.wheel_sha256 -cne $preflight.wheel_lease.sha256) { throw 'Post-safe wheel changed.' }
    Save-Caller
    Capture-Controller 'account-entry' @('-I','-B','-c',$entryCode,$gate,$Repo,$owned,$pinsJson,$caller.wheel_sha256,$entryPath)
    $caller.entry_completed = $true; Save-Caller
    foreach ($path in $pins.Keys) {
        $lease = [IO.File]::Open((Join-Path $Repo $path),[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        $sourceLeases.Add($lease)
        if ([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($lease)).ToLowerInvariant() -cne $pins[$path]) { throw 'Controller source changed after admission.' }
    }
    New-Item -ItemType Directory -Path $fixtureCwd | Out-Null
    # A fresh child of the already controller/SYSTEM-owned root inherits privacy.
    $cwdAcl = Get-Acl -LiteralPath $fixtureCwd
    if ($cwdAcl.GetOwner([Security.Principal.SecurityIdentifier]).Value -cne $controller.Value -or @(Get-ChildItem -LiteralPath $fixtureCwd -Force).Count) { throw 'Account working directory must be new, owned and empty.' }
    $env:PYTHONHOME = $null
    $env:PYTHONPATH = $null
    $env:PYTHONUSERBASE = $null
    $env:PYTHONNOUSERSITE = '1'
    Set-Location -LiteralPath $fixtureCwd
    # ALL paths were resolved before moving. The unchanged helper/C# protocol
    # remains one account/job, proof180s, driver150s and owned cleanup60s.
    $caller.fixture_invocation_attempted = $true; Save-Caller
    & $fixture -ExecuteApprovedFixture -ExecuteReviewedGuiLease -GuiHelper $helper -BasePython $basePython -Wheel $wheel -ProofScript $driver -Output $evidence -ControllerRepo $Repo -ComponentOwned $owned -ControllerPython $ControllerPython -AnchorPublisher $publisher -SourceManifest $manifest
    $caller.fixture_returned_normally = $true; Save-Caller
    $wheelLease.Position = 0
    if ([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($wheelLease)).ToLowerInvariant() -cne $caller.wheel_sha256) { throw 'Held wheel changed across fixture.' }
} catch { $caller.failure_type = $_.Exception.GetType().FullName }
finally {
    foreach ($lease in $sourceLeases) { try { $lease.Dispose() } catch { $caller.close_failures.Add($_.Exception.GetType().FullName) } }
    $caller.sources_closed = $sourceLeases.Count -eq 48 -and $caller.close_failures.Count -eq 0
    if ($wheelLease) { try { $wheelLease.Dispose(); $caller.wheel_closed=$true } catch { $caller.close_failures.Add($_.Exception.GetType().FullName) } }
    $caller.status = 'caller_returned'; Save-Caller
}
# Even a failed fixture's existing finally/cleanup and partial archives remain.
# The consumer refuses absent/blocked/unknown records; it never cleans resources.
Capture-Controller 'account-ack-gate' @('-I','-B',$gate,'--evidence',$evidence,'--protocol',(Join-Path $owned 'protocol'),'--output',$gateOutput)
if ($caller.failure_type -or -not $caller.fixture_returned_normally -or -not $caller.wheel_closed -or -not $caller.sources_closed -or $caller.close_failures.Count) { throw 'Account route refused; retain exact failure and cleanup ledger.' }
