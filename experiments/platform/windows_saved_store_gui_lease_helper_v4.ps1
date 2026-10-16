# ADDITIVE SOURCE PROPOSAL ONLY. Not wired to any workflow or account fixture.
# Contains no credential, account, logon, impersonation, Python or provider call.
[CmdletBinding()]
param(
    [switch]$StartReviewedGuiLease,
    [Parameter(Mandatory=$true)][string]$ControlDirectory,
    [Parameter(Mandatory=$true)][string]$Nonce,
    [Parameter(Mandatory=$true)][string]$UserSid,
    [Parameter(Mandatory=$true)][string]$ControllerSid,
    [ValidateRange(1,360)][int]$LeaseSeconds = 360
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $StartReviewedGuiLease) { throw 'GUI lease proposal is disabled.' }
if ($Nonce -cnotmatch '^[a-f0-9]{32}$') { throw 'Refuse an invalid scope nonce.' }
foreach ($sid in @($UserSid, $ControllerSid)) {
    if ([Security.Principal.SecurityIdentifier]::new($sid).Value -cne $sid) { throw 'Refuse a noncanonical SID.' }
}
if ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -cne $ControllerSid) { throw 'Refuse a different helper identity.' }
$control = Get-Item -LiteralPath $ControlDirectory -Force
if (-not $control.PSIsContainer -or ($control.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Refuse an invalid coordination directory.' }
if ($control.Name -cne ('gui-control-' + $Nonce)) { throw 'Refuse a changed coordination scope.' }
$acl = Get-Acl -LiteralPath $control.FullName
if (-not $acl.AreAccessRulesProtected -or $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -cne $ControllerSid) { throw 'Refuse unprotected coordination ownership.' }
$rules = @($acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier]))
if ($rules.Count -ne 2) { throw 'Refuse additional coordination access rules.' }
foreach ($sid in @($ControllerSid, 'S-1-5-18')) {
    $matched = @($rules | Where-Object { $_.IdentityReference.Value -ceq $sid -and $_.AccessControlType -eq 'Allow' -and $_.FileSystemRights -eq 'FullControl' -and -not $_.IsInherited })
    if ($matched.Count -ne 1) { throw 'Refuse different coordination access rights.' }
}
# STARTUPINFO uses no inherited handles; source/coordination are controller-only.
# The only allowed environment keys are supplied explicitly by the controller.
# Remove process-local search defaults before the unchanged finite-key guard.
$env:PATH = $null
$env:PATHEXT = $null
$actualKeys = @([Environment]::GetEnvironmentVariables().Keys | ForEach-Object { [string]$_ })
foreach ($key in $actualKeys) {
    if ($key -notin @('SystemRoot', 'TEMP', 'TMP', 'PSModulePath', 'POWERSHELL_DISTRIBUTION_CHANNEL')) {
        # PowerShell may synthesize its own module/channel keys. None is copied
        # from the controller environment; native launch passes only the first 3.
        throw 'Refuse an unexpected helper environment key.'
    }
}
Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Threading;
public sealed class T2PrivateGuiLease {
    [StructLayout(LayoutKind.Sequential)] struct SecurityAttributes {
        public uint length; public IntPtr descriptor;
        [MarshalAs(UnmanagedType.Bool)] public bool inherit;
    }
    [DllImport("user32.dll",SetLastError=true)] static extern IntPtr GetProcessWindowStation();
    [DllImport("user32.dll",SetLastError=true)] static extern IntPtr GetThreadDesktop(uint thread);
    [DllImport("user32.dll",SetLastError=true)] static extern bool SetProcessWindowStation(IntPtr station);
    [DllImport("user32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
    static extern IntPtr CreateWindowStationW(string name,uint flags,uint access,ref SecurityAttributes security);
    [DllImport("user32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
    static extern IntPtr CreateDesktopW(string name,IntPtr device,IntPtr mode,uint flags,uint access,ref SecurityAttributes security);
    [DllImport("user32.dll",SetLastError=true)] static extern bool CloseDesktop(IntPtr desktop);
    [DllImport("user32.dll",SetLastError=true)] static extern bool CloseWindowStation(IntPtr station);
    [DllImport("kernel32.dll")] static extern uint GetCurrentThreadId();
    [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr pointer);
    [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
    static extern bool ConvertStringSecurityDescriptorToSecurityDescriptorW(string text,uint revision,out IntPtr descriptor,out uint length);
    public sealed class Problem {
        public string Stage,Type; public int? NativeCode;
    }
    public sealed class Report {
        public uint MainThreadId, SetupThreadId;
        public bool SetupThreadExited, HelperStationRestored, HelperThreadDesktopUnchanged;
        public bool Ready, DesktopClosed, StationClosed, DescriptorFreed;
        public Problem PrimaryFailure;
        public List<Problem> TeardownFailures=new List<Problem>();
    }
    sealed class NativeFailure : Exception {
        public string Stage; public int Code;
        public NativeFailure(string stage,int code) : base(stage) { Stage=stage; Code=code; }
    }
    static void Require(bool ok,string stage) {
        if(!ok) throw new NativeFailure(stage,Marshal.GetLastWin32Error());
    }
    static Problem Describe(string stage,Exception error) {
        var p=new Problem(); p.Stage=stage; p.Type=error.GetType().Name;
        var native=error as NativeFailure;
        if(native!=null) { p.Stage=native.Stage; p.NativeCode=native.Code; }
        return p;
    }
    readonly string stationName,userSid,controllerSid;
    IntPtr station=IntPtr.Zero,desktop=IntPtr.Zero,descriptor=IntPtr.Zero;
    IntPtr oldStation=IntPtr.Zero,oldDesktop=IntPtr.Zero;
    public readonly Report State=new Report();
    public T2PrivateGuiLease(string stationName,string userSid,string controllerSid) {
        this.stationName=stationName; this.userSid=userSid; this.controllerSid=controllerSid;
    }
    public void Start() {
        State.MainThreadId=GetCurrentThreadId();
        try {
            oldStation=GetProcessWindowStation(); oldDesktop=GetThreadDesktop(State.MainThreadId);
            Require(oldStation!=IntPtr.Zero && oldDesktop!=IntPtr.Zero,"read_helper_gui_objects");
            var thread=new Thread(delegate() {
                State.SetupThreadId=GetCurrentThreadId();
                try {
                    var sddl="O:"+controllerSid+"D:P(A;;GA;;;"+controllerSid+")(A;;GA;;;"+userSid+")(A;;GA;;;SY)S:(ML;;NW;;;ME)";
                    uint length;
                    Require(ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl,1,out descriptor,out length),"private_desktop_descriptor");
                    var security=new SecurityAttributes(); security.length=(uint)Marshal.SizeOf(security);
                    security.descriptor=descriptor; security.inherit=false;
                    station=CreateWindowStationW(stationName,1,0x000f037f,ref security);
                    Require(station!=IntPtr.Zero,"create_private_window_station");
                    Require(SetProcessWindowStation(station),"select_helper_private_station");
                    desktop=CreateDesktopW("proof",IntPtr.Zero,IntPtr.Zero,0,0x000f01ff,ref security);
                    Require(desktop!=IntPtr.Zero,"create_private_desktop");
                    // CreateDesktop assigns THIS fresh thread. Its normal return
                    // releases thread-owned windows/hooks. Never TerminateThread.
                } catch(Exception error) { State.PrimaryFailure=Describe("gui_setup_thread",error); }
            });
            thread.IsBackground=true;
            thread.Start();
            if(!thread.Join(5000)) {
                State.PrimaryFailure=Describe("gui_setup_thread_join",new TimeoutException());
                return; // Caller writes failed report then exits WHOLE helper.
            }
            State.SetupThreadExited=true;
            try {
                Require(SetProcessWindowStation(oldStation),"restore_helper_station");
                Require(GetProcessWindowStation()==oldStation,"verify_helper_station");
                State.HelperStationRestored=true;
            } catch(Exception error) { State.TeardownFailures.Add(Describe("restore_helper_station",error)); }
            try {
                Require(GetCurrentThreadId()==State.MainThreadId && GetThreadDesktop(State.MainThreadId)==oldDesktop,"verify_helper_main_thread_desktop");
                State.HelperThreadDesktopUnchanged=true;
            } catch(Exception error) { State.TeardownFailures.Add(Describe("verify_helper_main_thread_desktop",error)); }
            State.Ready=State.PrimaryFailure==null && State.TeardownFailures.Count==0 &&
                State.SetupThreadExited && State.HelperStationRestored && State.HelperThreadDesktopUnchanged;
        } catch(Exception error) { State.PrimaryFailure=Describe("gui_setup_main",error); }
    }
    void Teardown(string stage,Action action) {
        try { action(); } catch(Exception error) { State.TeardownFailures.Add(Describe(stage,error)); }
    }
    public void Close() {
        State.Ready=false;
        if(!State.SetupThreadExited) return; // No resource races; whole process exit owns this case.
        if(desktop!=IntPtr.Zero) Teardown("close_private_desktop",delegate {
            Require(CloseDesktop(desktop),"close_private_desktop"); State.DesktopClosed=true; desktop=IntPtr.Zero;
        });
        else State.DesktopClosed=true;
        if(station!=IntPtr.Zero) Teardown("close_private_station",delegate {
            Require(CloseWindowStation(station),"close_private_station"); State.StationClosed=true; station=IntPtr.Zero;
        });
        else State.StationClosed=true;
        if(descriptor!=IntPtr.Zero) Teardown("free_private_gui_descriptor",delegate {
            Require(LocalFree(descriptor)==IntPtr.Zero,"free_private_gui_descriptor"); State.DescriptorFreed=true; descriptor=IntPtr.Zero;
        });
        else State.DescriptorFreed=true;
    }
}
'@
$lease = [T2PrivateGuiLease]::new(('AttuneT2-' + $Nonce), $UserSid, $ControllerSid)
$state = [ordered]@{
    revision = 3; nonce = $Nonce; state = 'starting'; process_sid = $ControllerSid
    station = ('AttuneT2-' + $Nonce); desktop = 'proof'; pid = $PID
    gui = $null; failure = $null
}
function Write-LeaseState {
    $state.gui = $lease.State
    $json = $state | ConvertTo-Json -Depth 8 -Compress
    if ([Text.Encoding]::UTF8.GetByteCount($json) -gt 4096) { throw 'Refuse an oversized lease record.' }
    $tmp = Join-Path $control.FullName 'state.tmp'
    $file = [IO.FileStream]::new($tmp, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes($json)
        $file.Write($bytes, 0, $bytes.Length)
        $file.Flush($true)
    } finally { $file.Dispose() }
    [IO.File]::Move($tmp, (Join-Path $control.FullName 'state.json'), $true)
}
$success = $false
try {
    $lease.Start()
    if (-not $lease.State.Ready) { throw 'Private GUI setup did not establish readiness.' }
    $state.state = 'ready'
    Write-LeaseState
    $clock = [Diagnostics.Stopwatch]::StartNew()
    $stop = Join-Path $control.FullName ('stop-' + $Nonce)
    while (-not [IO.File]::Exists($stop)) {
        if ($clock.Elapsed.TotalSeconds -ge $LeaseSeconds) { throw 'Private GUI lease deadline expired.' }
        Start-Sleep -Milliseconds 20
    }
    if ([IO.FileInfo]::new($stop).Length -ne 0) { throw 'Refuse a nonempty lease request.' }
    $success = $true
} catch {
    $state.failure = [ordered]@{ stage = 'gui_lease'; type = $_.Exception.GetType().Name }
} finally {
    $lease.Close()
    $success = $success -and $lease.State.DesktopClosed -and $lease.State.StationClosed -and
        $lease.State.DescriptorFreed -and $lease.State.TeardownFailures.Count -eq 0
    $state.state = $(if ($success) { 'stopped' } else { 'failed' })
    Write-LeaseState
}
if (-not $success) { [Environment]::Exit(125) }
