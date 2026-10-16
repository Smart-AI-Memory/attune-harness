# PROPOSAL ONLY. Not enabled by any workflow. Patrick must explicitly approve
# creating a disposable OS account and using its random credential first.
[CmdletBinding()]
param(
    [switch]$ExecuteApprovedFixture,
    [Parameter(Mandatory=$true)][string]$BasePython,
    [Parameter(Mandatory=$true)][string]$Wheel,
    [Parameter(Mandatory=$true)][string]$ProofScript,
    [Parameter(Mandatory=$true)][string]$Output
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $ExecuteApprovedFixture) { throw 'Proposal disabled. Explicit approval for the account/credential fixture is required.' }
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'This proposal is limited to a disposable GitHub-hosted Windows job.' }
if (Test-Path -LiteralPath $Output) { throw 'Evidence output must be new; retained evidence is never replaced.' }
foreach ($inputPath in @($BasePython, $Wheel, $ProofScript)) {
    if (-not [IO.Path]::IsPathRooted($inputPath) -or -not (Test-Path -LiteralPath $inputPath -PathType Leaf)) {
        throw 'Fixture inputs must be existing absolute files.'
    }
}

# This helper receives SecureString directly. The password reaches Win32 only
# in a zeroed unmanaged buffer, never an argv, environment value, file or log.
Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Security;
using System.Text;
public static class T2StandardProcess {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] struct Startup {
        public uint cb; public string reserved, desktop, title;
        public uint x,y,xsize,ysize,xchars,ychars,fill,flags;
        public ushort show, reserved2; public IntPtr reservedPointer, input, output, error;
    }
    [StructLayout(LayoutKind.Sequential)] struct ProcessInfo {
        public IntPtr process, thread; public uint pid, tid;
    }
    [StructLayout(LayoutKind.Sequential)] struct BasicLimits {
        public long processTime, jobTime; public uint flags;
        public UIntPtr minSet,maxSet; public uint activeLimit; public UIntPtr affinity;
        public uint priority,scheduling;
    }
    [StructLayout(LayoutKind.Sequential)] struct ExtendedLimits {
        public BasicLimits basic;
        public ulong readOps,writeOps,otherOps,readBytes,writeBytes,otherBytes;
        public UIntPtr processMemory,jobMemory,peakProcess,peakJob;
    }
    [StructLayout(LayoutKind.Sequential)] struct Accounting {
        public long user,kernel,periodUser,periodKernel;
        public uint faults,totalProcesses,activeProcesses,terminatedProcesses;
    }
    [StructLayout(LayoutKind.Sequential)] struct SecurityAttributes {
        public uint length; public IntPtr descriptor;
        [MarshalAs(UnmanagedType.Bool)] public bool inherit;
    }
    [DllImport("advapi32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern bool CreateProcessWithLogonW(string user,string domain,IntPtr password,uint logonFlags,
        string app,StringBuilder command,uint flags,IntPtr environment,string cwd,ref Startup startup,out ProcessInfo process);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr CreateJobObjectW(IntPtr sa,string name);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool SetInformationJobObject(IntPtr job,int cls,ref ExtendedLimits limits,uint bytes);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr job,IntPtr process);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool QueryInformationJobObject(IntPtr job,int cls,out Accounting accounting,uint bytes,IntPtr length);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool TerminateJobObject(IntPtr job,uint code);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool TerminateProcess(IntPtr process,uint code);
    [DllImport("kernel32.dll",SetLastError=true)] static extern uint ResumeThread(IntPtr thread);
    [DllImport("kernel32.dll",SetLastError=true)] static extern uint WaitForSingleObject(IntPtr handle,uint milliseconds);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetExitCodeProcess(IntPtr process,out uint code);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll")] static extern uint GetCurrentThreadId();
    [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr pointer);
    [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
    static extern bool ConvertStringSecurityDescriptorToSecurityDescriptorW(string text,uint revision,out IntPtr descriptor,out uint length);
    [DllImport("user32.dll",SetLastError=true)] static extern IntPtr GetProcessWindowStation();
    [DllImport("user32.dll",SetLastError=true)] static extern IntPtr GetThreadDesktop(uint thread);
    [DllImport("user32.dll",SetLastError=true)] static extern bool SetProcessWindowStation(IntPtr station);
    [DllImport("user32.dll",SetLastError=true)] static extern bool SetThreadDesktop(IntPtr desktop);
    [DllImport("user32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
    static extern IntPtr CreateWindowStationW(string name,uint flags,uint access,ref SecurityAttributes security);
    [DllImport("user32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
    static extern IntPtr CreateDesktopW(string name,IntPtr device,IntPtr mode,uint flags,uint access,ref SecurityAttributes security);
    [DllImport("user32.dll",SetLastError=true)] static extern bool CloseDesktop(IntPtr desktop);
    [DllImport("user32.dll",SetLastError=true)] static extern bool CloseWindowStation(IntPtr station);
    static void Check(bool ok,string operation) { if(!ok) throw new Win32Exception(Marshal.GetLastWin32Error(),operation); }
    static string Quote(string value) {
        var text=new StringBuilder("\""); int slashes=0;
        foreach(char ch in value) {
            if(ch=='\\') { slashes++; continue; }
            if(ch=='\"') text.Append('\\',slashes*2+1);
            else text.Append('\\',slashes);
            text.Append(ch); slashes=0;
        }
        return text.Append('\\',slashes*2).Append('"').ToString();
    }
    public sealed class Problem {
        public string Stage, Type; public int? NativeCode;
    }
    public sealed class RunReport {
        public uint? ExitCode;
        public bool ProcessCreated, JobAssigned, JobTerminationSucceeded;
        public bool WholeTreeEmptyConfirmed, RootExitConfirmed;
        public bool TreeDisappearanceEstablished, Success;
        public Problem PrimaryFailure;
        public List<Problem> TeardownFailures = new List<Problem>();
    }
    sealed class NativeFailure : Exception {
        public string Stage; public int NativeCode;
        public NativeFailure(string stage, int code) : base(stage) { Stage=stage; NativeCode=code; }
    }
    static void Require(bool ok,string stage) {
        if(!ok) throw new NativeFailure(stage,Marshal.GetLastWin32Error());
    }
    static Problem Describe(string stage,Exception error) {
        var result=new Problem(); result.Stage=stage; result.Type=error.GetType().Name;
        var native=error as NativeFailure;
        if(native!=null) { result.Stage=native.Stage; result.NativeCode=native.NativeCode; }
        return result; // No exception message, command line or secret enters a report.
    }
    static void Teardown(RunReport report,string stage,Action action) {
        try { action(); } catch(Exception error) { report.TeardownFailures.Add(Describe(stage,error)); }
    }
    public static RunReport Run(string user,string userSid,string controllerSid,SecureString password,
                                 string executable,string[] args,string cwd,string environment,uint timeout) {
        IntPtr secret=IntPtr.Zero, env=IntPtr.Zero, job=IntPtr.Zero;
        IntPtr station=IntPtr.Zero, desktop=IntPtr.Zero, descriptor=IntPtr.Zero;
        ProcessInfo process=new ProcessInfo(); var report=new RunReport();
        string phase="setup";
        try {
            // Only new noninteractive GUI objects receive new ACLs. Existing
            // WinSta0/Default objects and security policy remain untouched.
            var stationName="AttuneT2-"+Guid.NewGuid().ToString("N");
            var oldStation=GetProcessWindowStation(); var oldDesktop=GetThreadDesktop(GetCurrentThreadId());
            Require(oldStation!=IntPtr.Zero && oldDesktop!=IntPtr.Zero,"read_controller_gui_objects");
            var sddl="O:"+controllerSid+"D:P(A;;GA;;;"+controllerSid+")(A;;GA;;;"+userSid+")(A;;GA;;;SY)S:(ML;;NW;;;ME)";
            uint descriptorLength;
            Require(ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl,1,out descriptor,out descriptorLength),"private_desktop_descriptor");
            var security=new SecurityAttributes(); security.length=(uint)Marshal.SizeOf(security); security.descriptor=descriptor;
            station=CreateWindowStationW(stationName,1,0x000f037f,ref security);
            Require(station!=IntPtr.Zero,"create_private_window_station");
            try {
                Require(SetProcessWindowStation(station),"select_private_window_station");
                desktop=CreateDesktopW("proof",IntPtr.Zero,IntPtr.Zero,0,0x000f01ff,ref security);
                Require(desktop!=IntPtr.Zero,"create_private_desktop");
            } finally {
                // Restoration failures are recorded independently, preserving
                // any primary creation failure still propagating to the catch.
                Teardown(report,"restore_controller_station",delegate {
                    Require(SetProcessWindowStation(oldStation),"restore_controller_station");
                });
                Teardown(report,"restore_controller_desktop",delegate {
                    Require(SetThreadDesktop(oldDesktop),"restore_controller_desktop");
                });
            }
            if(report.TeardownFailures.Count!=0) throw new InvalidOperationException();
            job=CreateJobObjectW(IntPtr.Zero,null); Require(job!=IntPtr.Zero,"create_job");
            var limits=new ExtendedLimits(); limits.basic.flags=0x2000;
            Require(SetInformationJobObject(job,9,ref limits,(uint)Marshal.SizeOf(limits)),"set_job_kill_on_close");
            phase="prepare_logon_arguments";
            secret=Marshal.SecureStringToGlobalAllocUnicode(password);
            env=Marshal.StringToHGlobalUni(environment);
            var command=new StringBuilder(Quote(executable));
            foreach(string arg in args) command.Append(' ').Append(Quote(arg));
            if(command.Length>1023) throw new ArgumentException();
            var startup=new Startup(); startup.cb=(uint)Marshal.SizeOf(startup); startup.desktop=stationName+"\\proof";
            // Local interactive logon; no profile and no network-only mode.
            Require(CreateProcessWithLogonW(user,".",secret,0,executable,command,
                0x08000404,env,cwd,ref startup,out process),"create_actual_primary_process");
            report.ProcessCreated=true;
            Require(AssignProcessToJobObject(job,process.process),"assign_suspended_process_to_job");
            report.JobAssigned=true;
            Require(ResumeThread(process.thread)!=0xffffffff,"resume_process");
            phase="wait_process_deadline";
            uint wait=WaitForSingleObject(process.process,timeout);
            if(wait==0xffffffff) throw new NativeFailure("wait_process",Marshal.GetLastWin32Error());
            if(wait!=0) throw new TimeoutException();
            uint code; Require(GetExitCodeProcess(process.process,out code),"read_process_exit_code");
            report.ExitCode=code;
            phase="process_exit_nonzero";
            if(code!=0) throw new InvalidOperationException();
        } catch(Exception error) {
            report.PrimaryFailure=Describe(phase,error);
        } finally {
            // Every resource has an independent teardown path. None can bypass
            // secret zeroing or replace the primary failure with a later one.
            if(job!=IntPtr.Zero) {
                Teardown(report,"terminate_job",delegate {
                    Require(TerminateJobObject(job,125),"terminate_job");
                    report.JobTerminationSucceeded=true;
                });
                Teardown(report,"confirm_whole_tree_empty",delegate {
                    var clock=Stopwatch.StartNew();
                    do {
                        Accounting accounting;
                        Require(QueryInformationJobObject(job,1,out accounting,(uint)Marshal.SizeOf(typeof(Accounting)),IntPtr.Zero),"query_job_active_processes");
                        if(accounting.activeProcesses==0) { report.WholeTreeEmptyConfirmed=true; return; }
                        System.Threading.Thread.Sleep(20);
                    } while(clock.ElapsedMilliseconds<10000);
                    throw new TimeoutException();
                });
            }
            if(report.ProcessCreated && process.process!=IntPtr.Zero) {
                Teardown(report,"confirm_root_exit",delegate {
                    uint wait=WaitForSingleObject(process.process,0);
                    if(wait!=0) {
                        // Also contains an assignment failure: root was never
                        // resumed and cannot have spawned descendants.
                        Require(TerminateProcess(process.process,125),"terminate_root_fallback");
                        wait=WaitForSingleObject(process.process,10000);
                    }
                    if(wait==0xffffffff) throw new NativeFailure("wait_root_exit",Marshal.GetLastWin32Error());
                    if(wait!=0) throw new TimeoutException();
                    report.RootExitConfirmed=true;
                });
            }
            if(job!=IntPtr.Zero) Teardown(report,"close_job",delegate { Require(CloseHandle(job),"close_job"); });
            if(process.thread!=IntPtr.Zero) Teardown(report,"close_thread",delegate { Require(CloseHandle(process.thread),"close_thread"); });
            if(process.process!=IntPtr.Zero) Teardown(report,"close_process",delegate { Require(CloseHandle(process.process),"close_process"); });
            if(secret!=IntPtr.Zero) Teardown(report,"zero_logon_secret",delegate { Marshal.ZeroFreeGlobalAllocUnicode(secret); });
            if(env!=IntPtr.Zero) Teardown(report,"free_environment",delegate { Marshal.FreeHGlobal(env); });
            if(desktop!=IntPtr.Zero) Teardown(report,"close_private_desktop",delegate { Require(CloseDesktop(desktop),"close_private_desktop"); });
            if(station!=IntPtr.Zero) Teardown(report,"close_private_window_station",delegate { Require(CloseWindowStation(station),"close_private_window_station"); });
            if(descriptor!=IntPtr.Zero) Teardown(report,"free_security_descriptor",delegate {
                if(LocalFree(descriptor)!=IntPtr.Zero) throw new NativeFailure("free_security_descriptor",Marshal.GetLastWin32Error());
            });
        }
        report.TreeDisappearanceEstablished=!report.ProcessCreated ||
            (report.JobAssigned && report.JobTerminationSucceeded && report.WholeTreeEmptyConfirmed && report.RootExitConfirmed);
        report.Success=report.ExitCode==0 && report.PrimaryFailure==null &&
            report.TeardownFailures.Count==0 && report.TreeDisappearanceEstablished;
        return report;
    }
}
'@


# Execution remains disabled above unless Patrick approves this exact route.
# This non-secret report preserves the first setup failure and every cleanup
# issue separately; it is printed even if writing the evidence directory fails.
$nonce = [Guid]::NewGuid().ToString('N')
$accountName = 'ahT2' + $nonce.Substring(0, 12)
$fixtureRoot = Join-Path $env:ProgramData ('AttuneT2Proof-' + $nonce)
$createdSid = $null
$createdRoot = $false
$password = $null
$random = $null
$bytes = $null
$environment = $null
$proofAttempted = $false
$proofRun = $null
$privateCleanupRun = $null
$report = [ordered]@{
    proposal_revision = 2
    fixture_leaf = ('AttuneT2Proof-' + $nonce)
    account_name = $accountName
    account_sid = $null
    setup_failure = $null
    proof_run = $null
    private_cleanup_run = $null
    private_cleanup_succeeded = $false
    proof_tree_disappearance_established = $false
    cleanup_tree_disappearance_established = $false
    account_disable = 'not_created'
    account_remove = 'not_created'
    fixture_root_remove = 'not_created'
    credential_disposed = $false
    issues = [Collections.Generic.List[object]]::new()
    success = $false
}
function Get-SafeIssue([string]$stage, $failure) {
    # Do not report Exception.Message: a future library could include argv or
    # secret material. Stage, type and optional native error code suffice.
    $exception = $failure.Exception
    $nativeCode = $null
    if ($exception -is [ComponentModel.Win32Exception]) { $nativeCode = $exception.NativeErrorCode }
    return [ordered]@{ stage = $stage; type = $exception.GetType().Name; native_code = $nativeCode }
}
function Add-CleanupIssue([string]$stage, $failure) {
    $report.issues.Add((Get-SafeIssue $stage $failure))
}
function Get-ExactCreatedAccount {
    $accounts = @(Get-LocalUser -ErrorAction Stop)
    $named = @($accounts | Where-Object { $_.Name -eq $accountName })
    $owned = @($accounts | Where-Object { $_.SID.Value -eq $createdSid })
    if ($named.Count -gt 1 -or $owned.Count -gt 1 -or
        ($named.Count -eq 1 -and $named[0].SID.Value -ne $createdSid) -or
        ($owned.Count -eq 1 -and $owned[0].Name -ne $accountName)) {
        throw 'Refuse a changed account identity.'
    }
    if ($owned.Count -eq 1) { return $owned[0] }
    return $null
}
try {
    New-Item -ItemType Directory -Path $Output | Out-Null
    $password = [Security.SecureString]::new()
    try {
        $random = [Security.Cryptography.RandomNumberGenerator]::Create()
        $bytes = [byte[]]::new(32)
        $random.GetBytes($bytes)
        foreach ($character in 'Aa1!'.ToCharArray()) { $password.AppendChar($character) }
        $alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
        foreach ($value in $bytes) { $password.AppendChar($alphabet[$value -band 63]) }
        $password.MakeReadOnly()
    } finally {
        try { if ($bytes) { [Array]::Clear($bytes, 0, $bytes.Length) } }
        finally { if ($random) { $random.Dispose() } }
    }
    if (Get-LocalUser -ErrorAction Stop | Where-Object { $_.Name -eq $accountName }) { throw 'Refuse an existing account name.' }
    $account = New-LocalUser -Name $accountName -Password $password -AccountNeverExpires -PasswordNeverExpires -UserMayNotChangePassword
    $createdSid = $account.SID.Value
    $report.account_sid = $createdSid
    $report.account_disable = 'pending'
    $report.account_remove = 'pending'
    $users = Get-LocalGroup -SID 'S-1-5-32-545'
    if (-not (Get-LocalGroupMember -SID $users.SID | Where-Object { $_.SID.Value -eq $createdSid })) {
        Add-LocalGroupMember -SID $users.SID -Member $account
    }
    New-Item -ItemType Directory -Path $fixtureRoot | Out-Null
    $createdRoot = $true
    $report.fixture_root_remove = 'pending'
    $controllerSid = [Security.Principal.WindowsIdentity]::GetCurrent().User
    $acl = [Security.AccessControl.DirectorySecurity]::new()
    $acl.SetAccessRuleProtection($true, $false)
    $acl.SetOwner($controllerSid)
    foreach ($sid in @($controllerSid.Value, $createdSid, 'S-1-5-18')) {
        $identity = [Security.Principal.SecurityIdentifier]::new($sid)
        $rule = [Security.AccessControl.FileSystemAccessRule]::new($identity, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
        $acl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $fixtureRoot -AclObject $acl
    New-Item -ItemType Directory -Path (Join-Path $fixtureRoot 'tmp'), (Join-Path $fixtureRoot 'artifacts') | Out-Null
    Copy-Item -LiteralPath $ProofScript -Destination (Join-Path $fixtureRoot 'proof.py')
    $runtime = Join-Path $fixtureRoot 'runtime'
    & $BasePython -m venv $runtime
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the disposable runtime.' }
    # Trusted controller Python treats the child-writable runtime as data.
    & $BasePython -m pip --python $runtime install --no-index --no-deps $Wheel
    if ($LASTEXITCODE -ne 0) { throw 'Could not install the existing local wheel.' }
    $childPython = Join-Path $runtime 'Scripts/python.exe'
    $environment = 'SystemRoot=' + $env:SystemRoot + "`0TEMP=" + (Join-Path $fixtureRoot 'tmp') + "`0TMP=" + (Join-Path $fixtureRoot 'tmp') + "`0PYTHONUTF8=1`0`0"
    $proofAttempted = $true
    $proofRun = [T2StandardProcess]::Run($accountName, $createdSid, $controllerSid.Value, $password, $childPython,
        @('-I', (Join-Path $fixtureRoot 'proof.py'), '--current-standard', '--output', (Join-Path $fixtureRoot 'observations')),
        $fixtureRoot, $environment, 180000)
    $report.proof_run = $proofRun
    $report.proof_tree_disappearance_established = $proofRun.TreeDisappearanceEstablished
} catch {
    $report.setup_failure = Get-SafeIssue 'fixture_setup_or_invocation' $_
} finally {
    # Independent try/catch paths ensure a failed resource never skips the
    # remaining cleanup or the outermost SecureString disposal/report path.
    try {
        try {
            if ($createdSid -and $createdRoot -and $proofAttempted) {
                if ($proofRun -and $proofRun.TreeDisappearanceEstablished -and $proofRun.TeardownFailures.Count -eq 0) {
                    if ($proofRun.ProcessCreated) {
                        try {
                            $cleanup = "import pathlib,shutil,sys; r=pathlib.Path(sys.argv[1]); p=r/'observations'; assert r.name==sys.argv[2]; p.exists() and shutil.make_archive(str(r/'artifacts'/'observations'),'zip',str(p)); p.exists() and shutil.rmtree(p)"
                            $privateCleanupRun = [T2StandardProcess]::Run($accountName, $createdSid, $controllerSid.Value, $password, (Join-Path $fixtureRoot 'runtime/Scripts/python.exe'),
                                @('-I', '-c', $cleanup, $fixtureRoot, ('AttuneT2Proof-' + $nonce)), $fixtureRoot, $environment, 60000)
                            $report.private_cleanup_run = $privateCleanupRun
                            $report.cleanup_tree_disappearance_established = $privateCleanupRun.TreeDisappearanceEstablished
                            $report.private_cleanup_succeeded = $privateCleanupRun.Success
                        } catch { Add-CleanupIssue 'private_cleanup_invocation' $_ }
                    } else {
                        # Run reported no created process; no private child objects
                        # exist. This cannot cover an invocation that never returned.
                        $report.private_cleanup_succeeded = $true
                        $report.cleanup_tree_disappearance_established = $true
                    }
                } else {
                    $report.issues.Add([ordered]@{ stage = 'private_cleanup_blocked'; type = 'ProofTreeNotEstablished'; native_code = $null })
                }
            } elseif ($createdRoot -and -not $proofAttempted) {
                $report.private_cleanup_succeeded = $true
                $report.proof_tree_disappearance_established = $true
                $report.cleanup_tree_disappearance_established = $true
            }
        } catch { Add-CleanupIssue 'private_cleanup_phase' $_ }
        try {
            if ($createdRoot -and $report.private_cleanup_succeeded) {
                Get-ChildItem -LiteralPath (Join-Path $fixtureRoot 'artifacts') -File -ErrorAction Stop |
                    Copy-Item -Destination $Output -ErrorAction Stop
            }
        } catch { Add-CleanupIssue 'copy_synthetic_archive' $_ }
        try {
            if ($createdSid) {
                $ownedAccount = Get-ExactCreatedAccount
                if ($ownedAccount) { Disable-LocalUser -SID $ownedAccount.SID; $report.account_disable = 'succeeded' }
                else { $report.account_disable = 'already_absent' }
            }
        } catch { $report.account_disable = 'failed'; Add-CleanupIssue 'disable_exact_account_sid' $_ }
        try {
            if ($createdSid) {
                $ownedAccount = Get-ExactCreatedAccount
                if ($ownedAccount) { Remove-LocalUser -SID $ownedAccount.SID; $report.account_remove = 'succeeded' }
                else { $report.account_remove = 'already_absent' }
            }
        } catch { $report.account_remove = 'failed'; Add-CleanupIssue 'remove_exact_account_sid' $_ }
        try {
            if ($createdRoot) {
                if ($report.private_cleanup_succeeded -and $report.proof_tree_disappearance_established -and $report.cleanup_tree_disappearance_established) {
                    $item = Get-Item -LiteralPath $fixtureRoot -Force
                    if ($item.Name -ne ('AttuneT2Proof-' + $nonce) -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                        throw 'Refuse changed fixture root identity.'
                    }
                    Remove-Item -LiteralPath $fixtureRoot -Recurse -Force
                    $report.fixture_root_remove = 'succeeded'
                } else { $report.fixture_root_remove = 'blocked_tree_or_private_cleanup' }
            }
        } catch { $report.fixture_root_remove = 'failed'; Add-CleanupIssue 'remove_exact_fixture_root' $_ }
    } finally {
        try {
            if ($password) { $password.Dispose() }
            $report.credential_disposed = $true
        } catch { Add-CleanupIssue 'dispose_secure_string' $_ }
        $report.success = $report.setup_failure -eq $null -and $proofRun -and $proofRun.Success -and
            $report.private_cleanup_succeeded -and $report.proof_tree_disappearance_established -and
            $report.cleanup_tree_disappearance_established -and $report.account_remove -in @('succeeded', 'already_absent') -and
            $report.fixture_root_remove -eq 'succeeded' -and $report.credential_disposed -and $report.issues.Count -eq 0
        try {
            $report | ConvertTo-Json -Depth 12 | Set-Content (Join-Path $Output 'fixture.json') -Encoding utf8
        } catch { Add-CleanupIssue 'write_non_secret_report' $_; $report.success = $false }
        # CI logs retain the non-secret failure/ownership ledger even if the
        # output directory is unavailable. Credential content is never included.
        $report | ConvertTo-Json -Depth 12 | Write-Output
    }
}
if (-not $report.success) { throw 'The standard-user fixture failed. Inspect the non-secret cleanup ledger; ephemeral runner teardown owns reported residual resources.' }
