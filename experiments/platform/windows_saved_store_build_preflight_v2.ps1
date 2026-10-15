# Safe T2 build/controller evidence only. Never invoke the fixture, GUI or proof.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Repo,
    [Parameter(Mandatory=$true)][string]$ControllerPython,
    [Parameter(Mandatory=$true)][string]$Output,
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
    $wheel = (Get-ChildItem (Join-Path $owned 'wheel/attune_harness-*.whl')).FullName
    $manifest = (Resolve-Path (Join-Path $Repo 'experiments/platform/windows_saved_store_source_manifest_v3.json')).Path
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
if hashlib.sha256(raw).hexdigest()!='fcf8365fc00aeade30d8bdfa4c4f3e0f5ea869aabb1fbc1ce80466c3b999ae5a': raise ValueError('manifest_identity_refused')
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
$report = [ordered]@{ status = 'preflight_incomplete'; phase = 'source_pins'; source_observations = @(); post_source_observations = @(); commands = @(); canaries = @(); canary_markers = @(); startup = $null; failure_type = $null; failure_line = $null; fixture_invoked = $false; accounts_or_credentials_created = $false; gui_objects_created = $false; proof_invoked = $false; package_or_native_imported = $false; t2_d3_gate = 'unpassed'; production_port_allowed = $false }
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
    'experiments/platform/windows_saved_store_standard_user_gui_proposal_v3b3.ps1' = '696879df5b141def393235708f3a2baf0e8c9bb1cdb24d125082b53bc81a5804'
    'experiments/platform/windows_saved_store_gui_lease_helper_v4.ps1' = '5786e2eefbb6e61f65ef4caaf17a4668ad7dd14ae8f552d72dffcc21845729bf'
    'experiments/platform/windows_saved_store_helper_cold_compile_v1.ps1' = '496275b061b807302281834e036546361b5a1aa3651a3553c553b23db4db6885'
    'experiments/platform/windows_saved_store_combined_driver_v1.py' = 'e3aa0931328aabd2541b64b21f717c478b8121278dc7d10bb597e0cb0cf41937'
    'experiments/platform/windows_saved_store_proof.py' = 'b233497ffe18973eca3a4db29b2eca7ee5269c4ae2ef78429a8cf10db1ce7355'
    'experiments/platform/windows_saved_store_namespace_witness_v4.py' = 'f326803457453fccf02b795144ef1a48986c4c7068eef87aa56d21591ddd643e'
    'src/attune_harness/windows_effects.py' = 'ffc46d2f054a7bcf6c95230551a87fb5c73d9992ecebdde9497d2226d0763139'
    'experiments/platform/windows_saved_store_combined_driver_v2.py' = 'b61a452cb8f59862cee4a366510b74c73544d62e83dc4a81288e28b82e717ca0'
    'experiments/platform/windows_saved_store_source_manifest_v3.json' = 'fcf8365fc00aeade30d8bdfa4c4f3e0f5ea869aabb1fbc1ce80466c3b999ae5a'
    'experiments/platform/check_windows_saved_store_account_inputs_v3.py' = '7874a4819f18bf77dc0287b3895b0b05cceedec06d9cf3252d99e00f5b63555c'
    'experiments/platform/check_windows_saved_store_merge_inputs_v1.py' = '91d373245ace997eca32725ceea73f2131ef3ac1f39f5194f423f4cf15351559'
    'experiments/platform/project_windows_saved_store_build_v2.py' = 'c8ca4eafe05f14028d6d930e81f0cf42fa4d90d5cb2582914c1468b75bf3e0d8'
    '.github/workflows/windows-saved-store-reviewed-execution.yml' = '30e11a181edf79eecb0667686d2da540fe9c7047829dc31ddaa50e23d88dfc6e'
}
$pins['experiments/platform/windows_saved_store_build_preflight_v2.ps1'] = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
function Observe-Pins {
    foreach ($path in $pins.Keys) {
        $row = [ordered]@{ path = $path; expected_sha256 = $pins[$path]; actual_sha256 = $null; matched = $false; failure_type = $null }
        try { $row.actual_sha256 = (Get-FileHash -LiteralPath (Join-Path $Repo $path) -Algorithm SHA256).Hash.ToLowerInvariant(); $row.matched = $row.actual_sha256 -ceq $row.expected_sha256 } catch { $row.failure_type = $_.Exception.GetType().FullName }
        $row
    }
}
$exitCode = 1
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
    $projector = Join-Path $Repo 'experiments/platform/project_windows_saved_store_build_v2.py'
    $manifest = Join-Path $Repo 'experiments/platform/windows_saved_store_source_manifest_v3.json'
    $checker = Join-Path $Repo 'experiments/platform/check_windows_saved_store_account_inputs_v3.py'
    $driver = Join-Path $Repo 'experiments/platform/windows_saved_store_combined_driver_v2.py'
    $projection = Join-Path $Output 'source'
    $common = @('-I','-B',$projector,'--repo',$Repo,'--manifest',$manifest,'--projection',$projection)
    $report.phase = 'projection_create'; Save-Json $reportPath $report
    $null = Run-Recorded 'projection-create' $ControllerPython ($common + @('--output',(Join-Path $Output 'projection-created.json'))) 30
    $report.phase = 'projection_verify'; Save-Json $reportPath $report
    $null = Run-Recorded 'projection-verify' $ControllerPython ($common + @('--verify-only','--output',(Join-Path $Output 'projection-verified.json'))) 30
    $report.phase = 'projection_backend'; Save-Json $reportPath $report
    $null = Run-Recorded 'projection-build' $ControllerPython ($common + @('--build-output',(Join-Path $Output 'wheel'),'--output',(Join-Path $Output 'projection-build.json'))) 210
    $buildReceipt = Get-Content -LiteralPath (Join-Path $Output 'projection-build.json') -Raw | ConvertFrom-Json -AsHashtable
    if ($buildReceipt.status -cne 'projection_backend_returned' -or $buildReceipt.rows.Count -ne 116 -or
        $buildReceipt.backend_returned -cne $true -or $buildReceipt.backend_exit_code -ne 0 -or
        $buildReceipt.backend_isolated_python_requested -cne $true -or $buildReceipt.backend_argv[1] -cne '-I' -or
        $buildReceipt.backend_cwd -cne $projection) { throw 'Incomplete native backend invocation receipt.' }
    $report.post_source_observations = @(Observe-Pins); Save-Json $reportPath $report
    if (@($report.post_source_observations | Where-Object { -not $_.matched }).Count) { throw 'Source changed across backend; refuse startup.' }
    $wheels = @(Get-ChildItem (Join-Path $Output 'wheel/attune_harness-*.whl'))
    if ($wheels.Count -ne 1) { throw 'Require one new wheel.' }
    $report.phase = 'source116_wheel119'; Save-Json $reportPath $report
    $null = Run-Recorded 'wheel-check' $ControllerPython @('-I','-B',$checker,'--repo',$Repo,'--manifest',$manifest,'--driver',$driver,'--wheel',$wheels[0].FullName,'--output',(Join-Path $Output 'wheel119.json')) 30
    $wheelReceipt = Get-Content -LiteralPath (Join-Path $Output 'wheel119.json') -Raw | ConvertFrom-Json -AsHashtable
    if ($wheelReceipt.status -cne 'wheel_and_sources_verified' -or $wheelReceipt.source_rows.Count -ne 116 -or
        $wheelReceipt.wheel_rows.Count -ne 119 -or $wheelReceipt.wheel_platform -cne 'nt' -or $wheelReceipt.wheel_profile -cne 'nt_crlf' -or @($wheelReceipt.source_rows | Where-Object { $_.matched -cne $true }).Count -or
        @($wheelReceipt.wheel_rows | Where-Object { $_.matched -cne $true -or $_.record_matched -cne $true }).Count) { throw 'Incomplete native complete-wheel receipt.' }
    $report.phase = 'fresh_powershell_native_startup'; Save-Json $reportPath $report
    $null = Run-Recorded 'startup-child' (Join-Path $PSHOME 'pwsh.exe') @('-NoLogo','-NoProfile','-NonInteractive','-File',$PSCommandPath,'-Repo',$Repo,'-ControllerPython',$ControllerPython,'-Output',$Output,'-StartupChild') 240
    $report.startup = Get-Content -LiteralPath (Join-Path $Output 'startup.json') -Raw | ConvertFrom-Json -AsHashtable
    if ($report.startup.status -cne 'equivalent_module_startup_completed') { throw 'Incomplete startup evidence.' }
    $report.status = 'safe_build_and_module_startup_completed'; $report.phase = 'completed'; $exitCode = 0
} catch {
    $report.failure_type = $_.Exception.GetType().FullName
    $report.failure_line = $_.InvocationInfo.ScriptLineNumber
} finally {
    $report.canary_markers = @($report.canaries | ForEach-Object { [ordered]@{ name = $_.name; exists = (Test-Path -LiteralPath $_.marker) } })
    if (@($report.canary_markers | Where-Object { $_.exists }).Count) { $report.status = 'canary_loaded_refusal'; $exitCode = 1 }
    Save-Json $reportPath $report
}
exit $exitCode
