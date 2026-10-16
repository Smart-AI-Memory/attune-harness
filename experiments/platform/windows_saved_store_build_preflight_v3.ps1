# Safe T2 build/controller evidence only. Never invoke the fixture, GUI or proof.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Repo,
    [Parameter(Mandatory=$true)][string]$ControllerPython,
    [Parameter(Mandatory=$true)][string]$Output,
    [string]$Wheel,
    [string]$WheelSha256,
    [switch]$StartupChild
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Save-Json([string]$path, $value) {
    [IO.File]::WriteAllText($path, ($value | ConvertTo-Json -Depth 14), [Text.UTF8Encoding]::new($false))
}
function Require-PrivateRoot([string]$owned, $controller) {
    $item = Get-Item -LiteralPath $owned -Force
    if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Owned root must remain a plain directory.' }
    $acl = Get-Acl -LiteralPath $owned
    $rules = @($acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier]))
    if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -cne $controller.Value -or
        -not $acl.AreAccessRulesProtected -or $rules.Count -ne 2 -or
        @($rules | Where-Object { $_.IdentityReference.Value -ceq $controller.Value }).Count -ne 1 -or
        @($rules | Where-Object { $_.IdentityReference.Value -ceq 'S-1-5-18' }).Count -ne 1 -or
        @($rules | Where-Object { $_.IdentityReference.Value -notin @($controller.Value, 'S-1-5-18') -or
            $_.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or
            $_.FileSystemRights -ne [Security.AccessControl.FileSystemRights]::FullControl }).Count) { throw 'Owned root privacy changed.' }
}
function Protect-NewDirectory([string]$path, $controller) {
    if (Test-Path -LiteralPath $path) { throw 'Require a new owned directory.' }
    $null = New-Item -ItemType Directory -Path $path
    $acl = [Security.AccessControl.DirectorySecurity]::new()
    $acl.SetAccessRuleProtection($true, $false); $acl.SetOwner($controller)
    foreach ($sid in @($controller.Value, 'S-1-5-18')) {
        $identity = [Security.Principal.SecurityIdentifier]::new($sid)
        $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($identity, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow'))
    }
    Set-Acl -LiteralPath $path -AclObject $acl
    Require-PrivateRoot $path $controller
}

if ($StartupChild) {
    # Fresh pwsh child: resolve every path while still in the original checkout.
    # The actual native '& BasePython' calls below observe PowerShell's cwd route.
    $Repo = (Resolve-Path -LiteralPath $Repo).Path
    $ControllerPython = (Resolve-Path -LiteralPath $ControllerPython).Path
    $owned = (Resolve-Path (Join-Path $env:RUNNER_TEMP 'saved-store-build-safe')).Path
    if ($owned -cne $Output) { throw 'Refuse another startup output root.' }
    $controller = [Security.Principal.WindowsIdentity]::GetCurrent().User
    Require-PrivateRoot $owned $controller
    $wheel = $Wheel
    if ($wheel -cne (Join-Path $owned 'wheel/attune_harness-1.4.0-py3-none-any.whl') -or $WheelSha256 -cnotmatch '^[0-9a-f]{64}$') { throw 'Require the same admitted wheel path and hash.' }
    $wheelItem = Get-Item -LiteralPath $wheel -Force
    if ($wheelItem.PSIsContainer -or ($wheelItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
        (Get-FileHash -LiteralPath $wheel -Algorithm SHA256).Hash.ToLowerInvariant() -cne $WheelSha256) { throw 'Admitted wheel changed before startup.' }
    $manifest = (Resolve-Path (Join-Path $owned 'protocol/manifest.json')).Path
    $basePython = & $ControllerPython -I -c 'import sys; print(sys._base_executable)'
    if ($LASTEXITCODE -ne 0) { throw 'Base interpreter query failed.' }
    $runtime = Join-Path $owned 'fixture-equivalent-runtime'
    $runtimePython = Join-Path $runtime 'Scripts/python.exe'
    $startupOutput = Join-Path $owned 'startup.json'
    foreach ($absoluteInput in @($Repo, $ControllerPython, $owned, $wheel, $manifest, $basePython, $runtime, $runtimePython, $startupOutput)) {
        if (-not [IO.Path]::IsPathFullyQualified($absoluteInput)) { throw 'Require absolute startup inputs/outputs.' }
    }
    if (Test-Path -LiteralPath $startupOutput) { throw 'Refuse retained startup report.' }
    $startup = [ordered]@{ status = 'startup_incomplete'; phase = 'prepare_cwd'; seeded_python_key_names = @(); query = $null; query_stdout = @(); query_exit = $null; venv_exit = $null; pip_exit = $null; installed = $null; installed_stdout = @(); installed_exit = $null; failure_type = $null; failure_line = $null; accounts_or_credentials_created = $false; fixture_invoked = $false; gui_objects_created = $false; proof_invoked = $false; t2_d3_gate = 'unpassed'; production_port_allowed = $false }
    Save-Json $startupOutput $startup
    $childExit = 1
    try {
        $fixtureCwd = Join-Path $owned 'fixture-cwd'
        Protect-NewDirectory $fixtureCwd $controller
        if (@(Get-ChildItem -LiteralPath $fixtureCwd -Force).Count) { throw 'Startup working directory must start empty.' }
        # Synthetic process-only poison proves the three removals on this host.
        # Seed after the isolated base-interpreter lookup and before the exact scrub.
        $env:PYTHONHOME = $Repo
        $env:PYTHONPATH = $Repo
        $env:PYTHONUSERBASE = $Repo
        $startup.seeded_python_key_names = @('PYTHONHOME', 'PYTHONPATH', 'PYTHONUSERBASE')
        Save-Json $startupOutput $startup
        # Same process-only assignments as the accepted v3b fixture caller.
        $env:PYTHONHOME = $null
        $env:PYTHONPATH = $null
        $env:PYTHONUSERBASE = $null
        $env:PYTHONNOUSERSITE = '1'
        Set-Location -LiteralPath $fixtureCwd
        $startup.phase = 'actual_native_cwd_query'; Save-Json $startupOutput $startup
        $query = @'
import importlib.util,json,os,pathlib,sys
repo,cwd=map(pathlib.Path,sys.argv[1:])
names=sorted(k for k in os.environ if k.upper().startswith('PYTHON'))
metadata={'PYTHONLOCATION','PYTHON_ROOT_DIR','PYTHON2_ROOT_DIR','PYTHON3_ROOT_DIR'}
allowed=metadata|{'PYTHONNOUSERSITE'}
origins={name:importlib.util.find_spec(name).origin for name in ('venv','pip')}
paths=[str(pathlib.Path(p or os.getcwd()).resolve()) for p in sys.path]
checks={'actual_cwd':pathlib.Path(os.getcwd()).resolve()==cwd.resolve(),'original_repo_absent':str(repo.resolve()).casefold() not in [p.casefold() for p in paths],'user_site_disabled':sys.flags.no_user_site==1,'three_removed':not any(k.upper() in {'PYTHONHOME','PYTHONPATH','PYTHONUSERBASE'} for k in os.environ),'unknown_python_keys_absent':not(set(k.upper() for k in names)-allowed),'module_origins_outside_repo':all(not pathlib.Path(p).resolve().is_relative_to(repo.resolve()) for p in origins.values())}
print(json.dumps({'cwd':os.getcwd(),'executable':sys.executable,'base_prefix':sys.base_prefix,'sys_path':sys.path,'python_environment_key_names':names,'setup_action_metadata_key_names':[k for k in names if k.upper() in metadata],'no_user_site':sys.flags.no_user_site,'module_origins':origins,'checks':checks},ensure_ascii=True))
sys.exit(0 if all(checks.values()) else 41)
'@
        $startup.query_stdout = @(& $basePython -c $query $Repo $fixtureCwd)
        $startup.query_exit = $LASTEXITCODE
        Save-Json $startupOutput $startup
        if ($startup.query_exit -ne 0) { throw 'Actual native startup route refused.' }
        $startup.query = ($startup.query_stdout -join "`n") | ConvertFrom-Json -AsHashtable
        if ($startup.query.checks.Count -ne 6 -or @($startup.query.checks.Values | Where-Object { $_ -cne $true }).Count) { throw 'Incomplete actual startup observations.' }
        $startup.phase = 'basepython_m_venv'; Save-Json $startupOutput $startup
        & $basePython -m venv $runtime
        $startup.venv_exit = $LASTEXITCODE; Save-Json $startupOutput $startup
        if ($startup.venv_exit -ne 0) { throw 'Equivalent fixture venv failed.' }
        $startup.phase = 'basepython_m_pip'; Save-Json $startupOutput $startup
        & $basePython -m pip --python $runtime install --no-index --no-deps $wheel
        $startup.pip_exit = $LASTEXITCODE; Save-Json $startupOutput $startup
        if ($startup.pip_exit -ne 0) { throw 'Equivalent fixture pip failed.' }
        $startup.phase = 'installed_file_identity'; Save-Json $startupOutput $startup
        $installedQuery = @'
import hashlib,json,os,pathlib,sys,sysconfig
raw=pathlib.Path(sys.argv[1]).read_bytes()
if hashlib.sha256(raw).hexdigest()!='6b33976fcc9e7c1bcf276f82c9d4e0ad1d795008a74fb3c4343d86a7573c430a': raise ValueError('manifest_identity_refused')
m=json.loads(raw);profile={'posix':'posix_lf','nt':'nt_crlf'}.get(os.name)
if profile is None: raise ValueError('wheel_platform_refused')
members=dict(m['wheel_members']);members.update(m['wheel_platform_pairs'][profile])
site=pathlib.Path(sysconfig.get_paths()['purelib']);rows=[]
for name,expected in members.items():
    if name.endswith('/RECORD'): continue
    path=site/name;raw=path.read_bytes();rows.append({'path':name,'sha256':hashlib.sha256(raw).hexdigest(),'matched':len(raw)==expected['bytes'] and hashlib.sha256(raw).hexdigest()==expected['sha256']})
print(json.dumps({'site':str(site),'rows':rows,'archive_record_checked_before_install':True,'installer_rewritten_record_compared':False,'package_or_native_imported':False,'wheel_platform':os.name,'wheel_profile':profile},ensure_ascii=True))
sys.exit(0 if len(rows)==118 and all(row['matched'] for row in rows) else 42)
'@
        $startup.installed_stdout = @(& $runtimePython -I -c $installedQuery $manifest)
        $startup.installed_exit = $LASTEXITCODE; Save-Json $startupOutput $startup
        if ($startup.installed_exit -ne 0) { throw 'Installed file identity refused.' }
        $startup.installed = ($startup.installed_stdout -join "`n") | ConvertFrom-Json -AsHashtable
        if ($startup.installed.rows.Count -ne 118 -or $startup.installed.wheel_platform -cne 'nt' -or $startup.installed.wheel_profile -cne 'nt_crlf' -or @($startup.installed.rows | Where-Object { $_.matched -cne $true }).Count) { throw 'Incomplete installed file identity.' }
        $startup.status = 'equivalent_module_startup_completed'; $startup.phase = 'completed'; $childExit = 0
    } catch {
        $startup.failure_type = $_.Exception.GetType().FullName
        $startup.failure_line = $_.InvocationInfo.ScriptLineNumber
    } finally { Save-Json $startupOutput $startup }
    [Environment]::Exit($childExit)
}

$Repo = (Resolve-Path -LiteralPath $Repo).Path
$ControllerPython = (Resolve-Path -LiteralPath $ControllerPython).Path
if ($Output -cne (Join-Path $env:RUNNER_TEMP 'saved-store-build-safe')) { throw 'Require the finite new output root.' }
foreach ($absoluteInput in @($Repo, $ControllerPython, $Output)) {
    if (-not [IO.Path]::IsPathFullyQualified($absoluteInput)) { throw 'Require absolute preflight paths.' }
}
$controller = [Security.Principal.WindowsIdentity]::GetCurrent().User
Protect-NewDirectory $Output $controller
$reportPath = Join-Path $Output 'preflight.json'
$report = [ordered]@{ status = 'preflight_incomplete'; phase = 'source_pins'; source_observations = @(); post_source_observations = @(); commands = @(); component = $null; cold = $null; wheel_lease = $null; canaries = @(); canary_markers = @(); startup = $null; failure_type = $null; failure_line = $null; fixture_invoked = $false; accounts_or_credentials_created = $false; gui_objects_created = $false; proof_invoked = $false; package_or_native_imported = $false; t2_d3_gate = 'unpassed'; production_port_allowed = $false }
Save-Json $reportPath $report

# Managed bounded process/pipe operations, with no PInvoke, account or GUI type.
try {
Add-Type -TypeDefinition @'
using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading.Tasks;
public static class T2BuildCaptureV1 {
    public sealed class StreamCapture {
        readonly object gate=new object(); readonly StringBuilder text=new StringBuilder();
        long discarded; public string FailureType;
        public string Text {get{lock(gate){return text.ToString();}}}
        public long DiscardedCharacters {get{lock(gate){return discarded;}}}
        public void Drain(StreamReader reader) {
            try {var buffer=new char[1024];int count;
                while((count=reader.Read(buffer,0,buffer.Length))!=0) {lock(gate){int take=Math.Min(count,131072-text.Length);if(take>0)text.Append(buffer,0,take);discarded+=count-take;}}
            } catch(Exception error) {FailureType=error.GetType().FullName;}
        }
    }
    public sealed class Result {
        public int? ExitCode; public bool Started,TimedOut,KillTreeRequested,RootExitConfirmed,StreamsCompleted;
        public string FailureType; public StreamCapture Stdout=new StreamCapture(),Stderr=new StreamCapture();
    }
    public static Result Run(string executable,string[] argv,string cwd,int seconds) {
        if(seconds<1||seconds>300) throw new ArgumentException("finite_timeout");
        var result=new Result();var start=new ProcessStartInfo(executable){UseShellExecute=false,CreateNoWindow=true,
            RedirectStandardInput=true,RedirectStandardOutput=true,RedirectStandardError=true,WorkingDirectory=cwd};
        foreach(var arg in argv) start.ArgumentList.Add(arg);
        using(var process=new Process{StartInfo=start}) {
            try {
                result.Started=process.Start();if(!result.Started)throw new InvalidOperationException("start_false");process.StandardInput.Close();
                var stdout=Task.Run(()=>result.Stdout.Drain(process.StandardOutput));var stderr=Task.Run(()=>result.Stderr.Drain(process.StandardError));
                if(!process.WaitForExit(seconds*1000)) {result.TimedOut=true;result.KillTreeRequested=true;process.Kill(true);}
                result.RootExitConfirmed=process.WaitForExit(5000);
                if(result.RootExitConfirmed) result.ExitCode=process.ExitCode;
                result.StreamsCompleted=Task.WaitAll(new Task[]{stdout,stderr},5000);
                if(!result.RootExitConfirmed||!result.StreamsCompleted) throw new TimeoutException("capture_incomplete");
            } catch(Exception error) {result.FailureType=error.GetType().FullName;}
            finally {if(result.Started&&!process.HasExited){result.KillTreeRequested=true;try{process.Kill(true);result.RootExitConfirmed=process.WaitForExit(5000);}catch(Exception error){result.FailureType=error.GetType().FullName;}}}
        }
        return result;
    }
}
'@
} catch {
    $report.phase = 'managed_capture_compile'
    $report.failure_type = $_.Exception.GetType().FullName
    $report.failure_line = $_.InvocationInfo.ScriptLineNumber
    Save-Json $reportPath $report
    exit 1
}
function Run-Recorded([string]$name, [string]$executable, [string[]]$arguments, [int]$seconds, [int]$expectedExit = 0) {
    $row = [ordered]@{ name = $name; executable = $executable; argv = $arguments; requested_cwd = (Get-Location).Path; seconds = $seconds; expected_exit = $expectedExit; capture = $null; attempted = $true }
    $report.commands += $row; Save-Json $reportPath $report
    $row.capture = [T2BuildCaptureV1]::Run($executable, $arguments, $row.requested_cwd, $seconds)
    [IO.File]::WriteAllText((Join-Path $Output ($name + '-stdout.txt')), $row.capture.Stdout.Text, [Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $Output ($name + '-stderr.txt')), $row.capture.Stderr.Text, [Text.UTF8Encoding]::new($false))
    Save-Json $reportPath $report
    $r = $row.capture
    if (-not $r.Started -or $r.TimedOut -or $r.KillTreeRequested -or -not $r.RootExitConfirmed -or -not $r.StreamsCompleted -or
        $r.FailureType -or $r.Stdout.FailureType -or $r.Stderr.FailureType -or $r.Stdout.DiscardedCharacters -ne 0 -or
        $r.Stderr.DiscardedCharacters -ne 0 -or $r.ExitCode -ne $expectedExit) { throw 'Bounded command refused; inspect retained capture.' }
    return $row
}
$pins = [ordered]@{
    'experiments/platform/windows_saved_store_gui_lease_helper_v4.ps1' = '5786e2eefbb6e61f65ef4caaf17a4668ad7dd14ae8f552d72dffcc21845729bf'
    'experiments/platform/windows_saved_store_standard_user_gui_proposal_v3b3.ps1' = '696879df5b141def393235708f3a2baf0e8c9bb1cdb24d125082b53bc81a5804'
    'experiments/platform/windows_saved_store_proof.py' = 'b233497ffe18973eca3a4db29b2eca7ee5269c4ae2ef78429a8cf10db1ce7355'
    'experiments/platform/windows_saved_store_namespace_witness_v4.py' = 'f326803457453fccf02b795144ef1a48986c4c7068eef87aa56d21591ddd643e'
    'experiments/platform/windows_saved_store_combined_driver_v3.py' = '7ceb7519b2df1cca15729e3b96b0c0eba91f86b26cab97cbafe82752ef347a09'
    'experiments/platform/windows_saved_store_source_manifest_v4.json' = '6b33976fcc9e7c1bcf276f82c9d4e0ad1d795008a74fb3c4343d86a7573c430a'
    'requirements-workflow.lock' = '60ba53cfeba53c784331a689f948c5cbd046ed20f4e84fd6023eacf0ff656fad'
    'requirements-voyage.lock' = '6a2f18db82d16ec3e8c8da55b282a3f7627b9ae025fb7cb11d14b6f7b512e441'
    'requirements-mcp.lock' = '50f956aff914ee8ca2e85e00e3cc35aa56fff07213b659d962d7c9d91be94735'
    'requirements-tokens.lock' = '32fbeb94891432d45936d39b98513550e87405a278c3aaaabb714aa38c20de53'
    'requirements-redis.lock' = '84f43680576915e1e8716902d85acc6b2ae63a4451eb55f5eaddabbf9806c09c'
    'experiments/platform/check_windows_saved_store_account_inputs_v3.py' = '7874a4819f18bf77dc0287b3895b0b05cceedec06d9cf3252d99e00f5b63555c'
    'experiments/platform/project_windows_saved_store_build_v2.py' = 'c8ca4eafe05f14028d6d930e81f0cf42fa4d90d5cb2582914c1468b75bf3e0d8'
    'experiments/platform/windows_saved_store_helper_cold_compile_v1.ps1' = '496275b061b807302281834e036546361b5a1aa3651a3553c553b23db4db6885'
    'experiments/platform/windows_saved_store_component_adapter_v1.py' = 'a1cb9a2818b3a42f45ebb744fc890017f0f1a5f7129b47a4416b2ab7a0bfd9c3'
    'experiments/platform/windows_saved_store_component_route_v1.py' = '2020c0aa0ce28f53ccafdb684d04982e8cb4ccef9de98475a61b7215a7aa3141'
    '.github/workflows/windows-saved-store-reviewed-execution.yml' = '30e11a181edf79eecb0667686d2da540fe9c7047829dc31ddaa50e23d88dfc6e'
}
$pins['experiments/platform/windows_saved_store_build_preflight_v3.ps1'] = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
function Observe-Pins {
    foreach ($path in $pins.Keys) {
        $row = [ordered]@{ path = $path; expected_sha256 = $pins[$path]; actual_sha256 = $null; matched = $false; failure_type = $null }
        try { $row.actual_sha256 = (Get-FileHash -LiteralPath (Join-Path $Repo $path) -Algorithm SHA256).Hash.ToLowerInvariant(); $row.matched = $row.actual_sha256 -ceq $row.expected_sha256 } catch { $row.failure_type = $_.Exception.GetType().FullName }
        $row
    }
}
$exitCode = 1
$wheelLease = $null
try {
    $report.source_observations = @(Observe-Pins); Save-Json $reportPath $report
    if (@($report.source_observations | Where-Object { -not $_.matched }).Count) { throw 'Preflight source pin refused.' }
    $report.phase = 'capture_negative_control'; Save-Json $reportPath $report
    $capture = Run-Recorded 'capture-negative' $ControllerPython @('-I','-c','import sys; print("t2_build_capture_stdout"); print("t2_build_capture_stderr",file=sys.stderr); sys.exit(47)') 15 47
    if ($capture.capture.Stdout.Text.Trim() -cne 't2_build_capture_stdout' -or $capture.capture.Stderr.Text.Trim() -cne 't2_build_capture_stderr') { throw 'Deliberate failing child was not captured.' }
    $report.phase = 'canaries'; Save-Json $reportPath $report
    $names = @('setup.py','setup.cfg','venv.py','pip.py','sitecustomize.py','usercustomize.py')
    $existing = @([IO.Directory]::GetFileSystemEntries($Repo) | ForEach-Object { [IO.Path]::GetFileName($_) })
    foreach ($name in $names) { if ($existing -icontains $name) { throw 'Canary path already exists; preserve it and refuse.' } }
    foreach ($name in $names) {
        $marker = Join-Path $Output ('loaded-' + $name + '.marker')
        $body = if ($name -ceq 'setup.cfg') { "[metadata]`nversion = attr: t2_unreviewed_canary.version`n" } else {
            'from pathlib import Path' + "`n" + 'Path(' + ($marker | ConvertTo-Json -Compress) + ').write_text("t2_unreviewed_root_loaded", encoding="ascii")' + "`n" + 'raise RuntimeError("t2_unreviewed_root_loaded")' + "`n"
        }
        $bytes = [Text.Encoding]::UTF8.GetBytes($body)
        $stream = [IO.File]::Open((Join-Path $Repo $name), [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
        try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose() }
        [IO.File]::WriteAllBytes((Join-Path $Output ('canary-' + $name + '.txt')), $bytes)
        $report.canaries += [ordered]@{ name = $name; marker = $marker; sha256 = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant(); marker_existed_before = (Test-Path -LiteralPath $marker) }
        Save-Json $reportPath $report
    }
    $route = Join-Path $Repo 'experiments/platform/windows_saved_store_component_route_v1.py'
    $common = @('-I','-B',$route,'--repo',$Repo,'--owned',$Output)
    $report.phase = 'fixed_component_stage'; Save-Json $reportPath $report
    $null = Run-Recorded 'component-stage' $ControllerPython ($common + @('--mode','stage')) 180
    $report.component = Get-Content -LiteralPath (Join-Path $Output 'component-stage.json') -Raw | ConvertFrom-Json -AsHashtable
    if ($report.component.status -cne 'fixed_component_and_protocol_staged' -or $report.component.K.source_rows.Count -ne 116 -or
        $report.component.protocol_rows.Count -ne 11 -or $report.component.account_execution -cne $false) { throw 'Incomplete fixed component admission.' }
    $report.phase = 'cold_controls'; Save-Json $reportPath $report
    $cold = Join-Path $Repo 'experiments/platform/windows_saved_store_helper_cold_compile_v1.ps1'
    $null = Run-Recorded 'cold-controls' (Join-Path $PSHOME 'pwsh.exe') @('-NoLogo','-NoProfile','-NonInteractive','-File',$cold,'-Helper',(Join-Path $Output 'protocol/helper.ps1'),'-Output',(Join-Path $Output 'cold')) 180
    $report.cold = Get-Content -LiteralPath (Join-Path $Output 'cold/diagnostic.json') -Raw | ConvertFrom-Json -AsHashtable
    if ($report.cold.status -cne 'cold_compile_completed' -or $report.cold.cases.Count -ne 7 -or
        $report.cold.account_fixture_invoked -cne $false -or $report.cold.accounts_or_credentials_created -cne $false -or
        $report.cold.gui_objects_created -cne $false -or $report.cold.native_helper_constructed -cne $false -or
        $report.cold.storage_witness_invoked -cne $false -or $report.cold.production_port_allowed -cne $false) { throw 'Incomplete cold controls.' }
    $projection = Join-Path $Output 'source'
    $report.phase = 'projection_create'; Save-Json $reportPath $report
    $null = Run-Recorded 'projection-create' $ControllerPython ($common + @('--mode','create')) 30
    $report.phase = 'projection_verify'; Save-Json $reportPath $report
    $null = Run-Recorded 'projection-verify' $ControllerPython ($common + @('--mode','verify')) 30
    $report.phase = 'projection_backend'; Save-Json $reportPath $report
    $null = Run-Recorded 'projection-build' $ControllerPython ($common + @('--mode','build')) 210
    $buildReceipt = Get-Content -LiteralPath (Join-Path $Output 'projection-build.json') -Raw | ConvertFrom-Json -AsHashtable
    if ($buildReceipt.status -cne 'projection_backend_returned' -or $buildReceipt.rows.Count -ne 116 -or
        $buildReceipt.backend_returned -cne $true -or $buildReceipt.backend_exit_code -ne 0 -or
        $buildReceipt.backend_isolated_python_requested -cne $true -or $buildReceipt.backend_argv[1] -cne '-I' -or
        $buildReceipt.backend_cwd -cne $projection) { throw 'Incomplete native backend invocation receipt.' }
    $report.post_source_observations = @(Observe-Pins); Save-Json $reportPath $report
    if (@($report.post_source_observations | Where-Object { -not $_.matched }).Count) { throw 'Source changed across backend; refuse startup.' }
    $wheelPath = Join-Path $Output 'wheel/attune_harness-1.4.0-py3-none-any.whl'
    if (@(Get-ChildItem -LiteralPath (Join-Path $Output 'wheel') -Force).Count -ne 1) { throw 'Require exactly the finite wheel output.' }
    $wheelItem = Get-Item -LiteralPath $wheelPath -Force
    if ($wheelItem.PSIsContainer -or ($wheelItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Require a plain wheel before opening its lease.' }
    $report.wheel_lease = [ordered]@{ path = $wheelPath; sha256 = $null; denies_write_delete = $true; held_across_startup = $false; closed = $false; close_failure_type = $null }
    Save-Json $reportPath $report
    $wheelLease = [IO.File]::Open($wheelPath, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    $wheelHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($wheelLease)).ToLowerInvariant()
    $report.wheel_lease.sha256 = $wheelHash
    Save-Json $reportPath $report
    $report.phase = 'source116_wheel119'; Save-Json $reportPath $report
    $null = Run-Recorded 'wheel-check' $ControllerPython ($common + @('--mode','wheel')) 30
    $wheelReceipt = Get-Content -LiteralPath (Join-Path $Output 'wheel119.json') -Raw | ConvertFrom-Json -AsHashtable
    if ($wheelReceipt.wheel_sha256 -cne $wheelHash -or $wheelReceipt.status -cne 'wheel_and_sources_verified' -or $wheelReceipt.source_rows.Count -ne 116 -or
        $wheelReceipt.wheel_rows.Count -ne 119 -or $wheelReceipt.wheel_platform -cne 'nt' -or $wheelReceipt.wheel_profile -cne 'nt_crlf' -or @($wheelReceipt.source_rows | Where-Object { $_.matched -cne $true }).Count -or
        @($wheelReceipt.wheel_rows | Where-Object { $_.matched -cne $true -or $_.record_matched -cne $true }).Count) { throw 'Incomplete native complete-wheel receipt.' }
    $report.phase = 'fresh_powershell_native_startup'; Save-Json $reportPath $report
    $null = Run-Recorded 'startup-child' (Join-Path $PSHOME 'pwsh.exe') @('-NoLogo','-NoProfile','-NonInteractive','-File',$PSCommandPath,'-Repo',$Repo,'-ControllerPython',$ControllerPython,'-Output',$Output,'-Wheel',$wheelPath,'-WheelSha256',$wheelHash,'-StartupChild') 240
    $report.startup = Get-Content -LiteralPath (Join-Path $Output 'startup.json') -Raw | ConvertFrom-Json -AsHashtable
    if ($report.startup.status -cne 'equivalent_module_startup_completed') { throw 'Incomplete startup evidence.' }
    $wheelLease.Position = 0
    if ([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($wheelLease)).ToLowerInvariant() -cne $wheelHash) { throw 'Admitted wheel object changed across startup.' }
    $report.wheel_lease.held_across_startup = $true
    $report.status = 'safe_build_and_module_startup_completed'; $report.phase = 'completed'; $exitCode = 0
} catch {
    $report.failure_type = $_.Exception.GetType().FullName
    $report.failure_line = $_.InvocationInfo.ScriptLineNumber
} finally {
    if ($null -ne $wheelLease) {
        try { $wheelLease.Dispose(); $report.wheel_lease.closed = $true }
        catch { $report.wheel_lease.close_failure_type = $_.Exception.GetType().FullName; $report.status = 'wheel_lease_cleanup_refused'; $exitCode = 1 }
    }
    $report.canary_markers = @($report.canaries | ForEach-Object { [ordered]@{ name = $_.name; exists = (Test-Path -LiteralPath $_.marker) } })
    if (@($report.canary_markers | Where-Object { $_.exists }).Count) { $report.status = 'canary_loaded_refusal'; $exitCode = 1 }
    Save-Json $reportPath $report
}
exit $exitCode
