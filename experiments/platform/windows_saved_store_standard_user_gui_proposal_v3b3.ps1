# ADDITIVE GUI ISOLATION PROPOSAL v3. SOURCE REVIEW ONLY.
# Not enabled by any workflow. No execution or credential retry is approved.
[CmdletBinding()]
param(
    [switch]$ExecuteApprovedFixture,
    [switch]$ExecuteReviewedGuiLease,
    [Parameter(Mandatory=$true)][string]$GuiHelper,
    [Parameter(Mandatory=$true)][string]$BasePython,
    [Parameter(Mandatory=$true)][string]$Wheel,
    [Parameter(Mandatory=$true)][string]$ProofScript,
    [Parameter(Mandatory=$true)][string]$Output
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $ExecuteApprovedFixture -or -not $ExecuteReviewedGuiLease) { throw 'GUI isolation revision disabled. Review and explicit route authorization are required.' }
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'This proposal is limited to a disposable GitHub-hosted Windows job.' }
if (Test-Path -LiteralPath $Output) { throw 'Evidence output must be new; retained evidence is never replaced.' }
foreach ($inputPath in @($BasePython, $Wheel, $ProofScript, $GuiHelper)) {
    if (-not [IO.Path]::IsPathRooted($inputPath) -or -not (Test-Path -LiteralPath $inputPath -PathType Leaf)) {
        throw 'Fixture inputs must be existing absolute files.'
    }
}

$ExpectedGuiHelperSHA256 = '5786e2eefbb6e61f65ef4caaf17a4668ad7dd14ae8f552d72dffcc21845729bf'
if ((Get-FileHash -LiteralPath $GuiHelper -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ExpectedGuiHelperSHA256) { throw 'Refuse different GUI helper source.' }

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
    [DllImport("user32.dll",SetLastError=true)] static extern IntPtr GetProcessWindowStation();
    [DllImport("user32.dll",SetLastError=true)] static extern IntPtr GetThreadDesktop(uint thread);
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
        public bool TreeDisappearanceEstablished, ControllerGuiUnchanged, Success;
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
                                 string executable,string[] args,string cwd,string environment,string desktopPath,uint timeout) {
        IntPtr secret=IntPtr.Zero, env=IntPtr.Zero, job=IntPtr.Zero;
        IntPtr originalStation=IntPtr.Zero, originalDesktop=IntPtr.Zero;
        uint originalThread=0;
        ProcessInfo process=new ProcessInfo(); var report=new RunReport();
        string phase="setup";
        try {
            // Read-only controller invariant; all GUI mutation lives in a
            // distinct same-identity helper process with no credential input.
            originalThread=GetCurrentThreadId();
            originalStation=GetProcessWindowStation(); originalDesktop=GetThreadDesktop(originalThread);
            Require(originalStation!=IntPtr.Zero && originalDesktop!=IntPtr.Zero,"read_controller_gui_objects");
            if(!System.Text.RegularExpressions.Regex.IsMatch(desktopPath,"\\AAttuneT2-[a-f0-9]{32}\\\\proof\\z")) throw new ArgumentException();
            job=CreateJobObjectW(IntPtr.Zero,null); Require(job!=IntPtr.Zero,"create_job");
            var limits=new ExtendedLimits(); limits.basic.flags=0x2000;
            Require(SetInformationJobObject(job,9,ref limits,(uint)Marshal.SizeOf(limits)),"set_job_kill_on_close");
            phase="prepare_logon_arguments";
            secret=Marshal.SecureStringToGlobalAllocUnicode(password);
            env=Marshal.StringToHGlobalUni(environment);
            var command=new StringBuilder(Quote(executable));
            foreach(string arg in args) command.Append(' ').Append(Quote(arg));
            if(command.Length>1023) throw new ArgumentException();
            var startup=new Startup(); startup.cb=(uint)Marshal.SizeOf(startup); startup.desktop=desktopPath;
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
            Teardown(report,"verify_original_controller_gui",delegate {
                report.ControllerGuiUnchanged=originalThread!=0 && GetCurrentThreadId()==originalThread &&
                    GetProcessWindowStation()==originalStation && GetThreadDesktop(originalThread)==originalDesktop;
                if(!report.ControllerGuiUnchanged) throw new InvalidOperationException();
            });
        }
        report.TreeDisappearanceEstablished=!report.ProcessCreated ||
            (report.JobAssigned && report.JobTerminationSucceeded && report.WholeTreeEmptyConfirmed && report.RootExitConfirmed);
        report.Success=report.ExitCode==0 && report.PrimaryFailure==null &&
            report.TeardownFailures.Count==0 && report.TreeDisappearanceEstablished && report.ControllerGuiUnchanged;
        return report;
    }
}
'@

# Credential-free helper lifecycle. This is compiled data until the reviewed route is invoked.
Add-Type -TypeDefinition @'
// ADDITIVE SOURCE PROPOSAL ONLY. No credential/account/logon/impersonation API.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Security.Cryptography;
using Microsoft.Win32.SafeHandles;
public sealed class T2GuiLeaseController {
    [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)] struct Startup {
        public uint cb; public string reserved,desktop,title;
        public uint x,y,xsize,ysize,xchars,ychars,fill,flags;
        public ushort show,reserved2; public IntPtr reservedPointer,input,output,error;
    }
    [StructLayout(LayoutKind.Sequential)] struct ProcessInfo { public IntPtr process,thread; public uint pid,tid; }
    [StructLayout(LayoutKind.Sequential)] struct BasicLimits {
        public long processTime,jobTime; public uint flags;
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
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
    static extern bool CreateProcessW(string app,StringBuilder command,IntPtr processSecurity,IntPtr threadSecurity,
        bool inherit,uint flags,IntPtr environment,string cwd,ref Startup startup,out ProcessInfo process);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr CreateJobObjectW(IntPtr sa,string name);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool SetInformationJobObject(IntPtr job,int cls,ref ExtendedLimits limits,uint bytes);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr job,IntPtr process);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool QueryInformationJobObject(IntPtr job,int cls,out Accounting accounting,uint bytes,IntPtr length);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool TerminateJobObject(IntPtr job,uint code);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool TerminateProcess(IntPtr process,uint code);
    [DllImport("kernel32.dll",SetLastError=true)] static extern uint ResumeThread(IntPtr thread);
    [DllImport("kernel32.dll",SetLastError=true)] static extern uint WaitForSingleObject(IntPtr handle,uint ms);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetExitCodeProcess(IntPtr process,out uint code);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll")] static extern uint GetCurrentThreadId();
    [DllImport("user32.dll",SetLastError=true)] static extern IntPtr GetProcessWindowStation();
    [DllImport("user32.dll",SetLastError=true)] static extern IntPtr GetThreadDesktop(uint thread);
    [StructLayout(LayoutKind.Sequential)] struct FileTime { public uint low,high; }
    [StructLayout(LayoutKind.Sequential)] struct FileInfo {
        public uint attributes; public FileTime creation,access,write;
        public uint volume,sizeHigh,sizeLow,links,indexHigh,indexLow;
    }
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
    static extern IntPtr CreateFileW(string name,uint access,uint sharing,IntPtr security,uint disposition,uint flags,IntPtr template);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetFileInformationByHandle(IntPtr handle,out FileInfo info);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern uint GetFinalPathNameByHandleW(IntPtr handle,StringBuilder name,uint size,uint flags);
    // Deliberately no CreateDesktop/SetThreadDesktop/SetProcessWindowStation imports.
    public sealed class Problem { public string Stage,Type; public int? NativeCode; }
    public sealed class Snapshot {
        public uint ThreadId; public long Station,Desktop;
    }
    public sealed class Binding {
        public string Leaf,Kind; public uint Volume; public ulong FileId;
    }
    public sealed class Report {
        public bool ProcessCreated,JobAssigned,JobTerminationSucceeded;
        public bool WholeTreeEmptyConfirmed,RootExitConfirmed,TreeDisappearanceEstablished;
        public bool OpenGuiUnchanged,CloseGuiUnchanged;
        public bool HelperSourceRetained,SourceReleaseSucceeded,AncestorReleaseSucceeded;
        public string RetainedSourceSha256;
        public List<Binding> PathBindings=new List<Binding>();
        public uint? Pid,ExitCode;
        public Snapshot BeforeOpen,AfterOpen,BeforeClose,AfterClose;
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
    static string Quote(string value) {
        var text=new StringBuilder("\""); int slashes=0;
        foreach(char ch in value) {
            if(ch=='\\') { slashes++; continue; }
            if(ch=='\"') text.Append('\\',slashes*2+1); else text.Append('\\',slashes);
            text.Append(ch); slashes=0;
        }
        return text.Append('\\',slashes*2).Append('"').ToString();
    }
    static Snapshot ReadGui() {
        var s=new Snapshot(); s.ThreadId=GetCurrentThreadId();
        s.Station=GetProcessWindowStation().ToInt64(); s.Desktop=GetThreadDesktop(s.ThreadId).ToInt64();
        Require(s.Station!=0 && s.Desktop!=0,"read_controller_gui_identity"); return s;
    }
    static bool Same(Snapshot a,Snapshot b) {
        return a!=null && b!=null && a.ThreadId==b.ThreadId && a.Station==b.Station && a.Desktop==b.Desktop;
    }
    void Teardown(string stage,Action action) {
        try { action(); } catch(Exception error) { State.TeardownFailures.Add(Describe(stage,error)); }
    }
    readonly List<IntPtr> directories=new List<IntPtr>();
    readonly HashSet<string> directoryPaths=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
    FileStream sourceLease;
    static string CanonicalPath(string path) {
        if(path==null || path.Length>1024 || !System.Text.RegularExpressions.Regex.IsMatch(path,@"\A[A-Za-z]:\\") ||
           !String.Equals(Path.GetFullPath(path),path,StringComparison.OrdinalIgnoreCase)) throw new ArgumentException();
        string[] parts=path.Substring(3).Split('\\');
        if(parts.Length>32) throw new ArgumentException();
        foreach(var part in parts) {
            if(part.Length==0 || part=="." || part==".." || part.EndsWith(".",StringComparison.Ordinal) ||
               part.EndsWith(" ",StringComparison.Ordinal) || part.IndexOfAny(new char[]{':','<','>','"','|','?','*'})>=0) throw new ArgumentException();
            foreach(char ch in part) if(ch<32) throw new ArgumentException();
            var stem=part.Split('.')[0];
            if(System.Text.RegularExpressions.Regex.IsMatch(stem,@"\A(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])\z",System.Text.RegularExpressions.RegexOptions.IgnoreCase)) throw new ArgumentException();
        }
        return path;
    }
    void CheckNormalizedName(IntPtr handle,string expected) {
        var name=new StringBuilder(2048);
        uint size=GetFinalPathNameByHandleW(handle,name,(uint)name.Capacity,0);
        Require(size!=0,"read_normalized_helper_path");
        if(size>=name.Capacity || !String.Equals(name.ToString(),@"\\?\"+expected,StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException();
    }
    FileInfo CheckFile(IntPtr handle,bool directory,string phase) {
        FileInfo info; Require(GetFileInformationByHandle(handle,out info),phase);
        if((info.attributes&0x400)!=0 || ((info.attributes&0x10)!=0)!=directory || (!directory && info.links!=1)) throw new InvalidOperationException();
        return info;
    }
    void RetainAncestors(string fullDirectory) {
        CanonicalPath(fullDirectory);
        var paths=new List<string>(); string current=fullDirectory;
        while(current!=null) { paths.Add(current); current=Path.GetDirectoryName(current); }
        paths.Reverse();
        foreach(var path in paths) {
            if(directoryPaths.Contains(path)) continue;
            // Each earlier component is retained before opening the next one.
            // OPEN_REPARSE_POINT inspects each final component without following
            // it; no FILE_SHARE_DELETE permits ancestor rename/replacement.
            IntPtr handle=CreateFileW(path,0x81,3,IntPtr.Zero,3,0x02200000,IntPtr.Zero);
            Require(handle!=new IntPtr(-1),"retain_helper_ancestor");
            directories.Add(handle); directoryPaths.Add(path);
            var info=CheckFile(handle,true,"inspect_helper_ancestor");
            CheckNormalizedName(handle,path);
            State.PathBindings.Add(new Binding { Leaf=Path.GetFileName(path),Kind="directory",Volume=info.volume,FileId=((ulong)info.indexHigh<<32)|info.indexLow });
        }
    }
    void RetainSource(string helper,string expectedHash,string directory) {
        CanonicalPath(helper); CanonicalPath(directory);
        if(!String.Equals(Path.GetDirectoryName(helper),directory,StringComparison.OrdinalIgnoreCase)) throw new ArgumentException();
        if(!System.Text.RegularExpressions.Regex.IsMatch(expectedHash,@"\A[a-f0-9]{64}\z")) throw new ArgumentException();
        RetainAncestors(directory);
        // Deny both write and delete for the exact, non-reparse, one-link source
        // object until the helper process and its tree are stopped.
        IntPtr raw=CreateFileW(helper,0x80000000,1,IntPtr.Zero,3,0x00200000,IntPtr.Zero);
        Require(raw!=new IntPtr(-1),"retain_helper_source");
        var safe=new SafeFileHandle(raw,true);
        try {
            var info=CheckFile(raw,false,"inspect_helper_source");
            CheckNormalizedName(raw,helper);
            if(info.sizeHigh!=0 || info.sizeLow>262144) throw new InvalidOperationException();
            sourceLease=new FileStream(safe,FileAccess.Read);
            safe=null; // FileStream owns it now.
            string hash;
            using(var sha=SHA256.Create()) hash=BitConverter.ToString(sha.ComputeHash(sourceLease)).Replace("-","").ToLowerInvariant();
            if(!String.Equals(hash,expectedHash,StringComparison.Ordinal)) throw new InvalidOperationException();
            sourceLease.Position=0;
            State.RetainedSourceSha256=hash; State.HelperSourceRetained=true;
            State.PathBindings.Add(new Binding { Leaf=Path.GetFileName(helper),Kind="source",Volume=info.volume,FileId=((ulong)info.indexHigh<<32)|info.indexLow });
        } finally { if(safe!=null) safe.Dispose(); }
    }
    IntPtr job=IntPtr.Zero;
    ProcessInfo process=new ProcessInfo();
    bool closed;
    public readonly Report State=new Report();
    public void Open(string executable,string helper,string expectedHelperHash,string directory,string nonce,string userSid,string controllerSid,string systemRoot) {
        IntPtr environment=IntPtr.Zero;
        try {
            State.BeforeOpen=ReadGui();
            foreach(var path in new string[]{executable,helper,directory,systemRoot})
                if(!Path.IsPathFullyQualified(path) || path.IndexOf('\0')>=0) throw new ArgumentException();
            if(!System.Text.RegularExpressions.Regex.IsMatch(nonce,"\\A[a-f0-9]{32}\\z")) throw new ArgumentException();
            RetainSource(helper,expectedHelperHash,directory);
            job=CreateJobObjectW(IntPtr.Zero,null); Require(job!=IntPtr.Zero,"create_helper_job");
            var limits=new ExtendedLimits(); limits.basic.flags=0x2000;
            Require(SetInformationJobObject(job,9,ref limits,(uint)Marshal.SizeOf(limits)),"helper_job_kill_on_close");
            var args=new string[]{"-NoLogo","-NoProfile","-NonInteractive","-File",helper,"-StartReviewedGuiLease",
                "-ControlDirectory",directory,"-Nonce",nonce,"-UserSid",userSid,"-ControllerSid",controllerSid,"-LeaseSeconds","360"};
            var command=new StringBuilder(Quote(executable));
            foreach(var arg in args) command.Append(' ').Append(Quote(arg));
            if(command.Length>8191) throw new ArgumentException();
            // Explicit non-secret environment. Never inherit controller/provider/auth keys.
            string temp=Path.Combine(directory,"tmp");
            environment=Marshal.StringToHGlobalUni("SystemRoot="+systemRoot+"\0TEMP="+temp+"\0TMP="+temp+"\0\0");
            var startup=new Startup(); startup.cb=(uint)Marshal.SizeOf(startup);
            Require(CreateProcessW(executable,command,IntPtr.Zero,IntPtr.Zero,false,0x08000404,environment,directory,ref startup,out process),"create_same_identity_gui_helper");
            State.ProcessCreated=true; State.Pid=process.pid;
            Require(AssignProcessToJobObject(job,process.process),"assign_suspended_gui_helper"); State.JobAssigned=true;
            Require(ResumeThread(process.thread)!=0xffffffff,"resume_gui_helper");
        } catch(Exception error) { State.PrimaryFailure=Describe("open_gui_helper",error); }
        finally {
            if(environment!=IntPtr.Zero) Marshal.FreeHGlobal(environment); // Contains no credential.
            Teardown("verify_controller_gui_after_open",delegate {
                State.AfterOpen=ReadGui(); State.OpenGuiUnchanged=Same(State.BeforeOpen,State.AfterOpen);
                if(!State.OpenGuiUnchanged) throw new InvalidOperationException();
            });
        }
    }
    public bool HasExited() {
        if(!State.ProcessCreated) return true;
        uint wait=WaitForSingleObject(process.process,0);
        if(wait==0xffffffff) throw new NativeFailure("poll_gui_helper",Marshal.GetLastWin32Error());
        return wait==0;
    }
    public void Close() {
        if(closed) return;
        closed=true;
        Teardown("read_controller_gui_before_close",delegate { State.BeforeClose=ReadGui(); });
        if(State.ProcessCreated) Teardown("wait_gui_helper_stop",delegate {
            uint wait=WaitForSingleObject(process.process,10000);
            if(wait==0xffffffff) throw new NativeFailure("wait_gui_helper_stop",Marshal.GetLastWin32Error());
            if(wait!=0) throw new TimeoutException();
            uint code; Require(GetExitCodeProcess(process.process,out code),"read_gui_helper_exit"); State.ExitCode=code;
            if(code!=0) throw new InvalidOperationException();
        });
        if(job!=IntPtr.Zero) {
            Teardown("terminate_gui_helper_job",delegate {
                Require(TerminateJobObject(job,125),"terminate_gui_helper_job"); State.JobTerminationSucceeded=true;
            });
            Teardown("confirm_gui_helper_tree_empty",delegate {
                var clock=Stopwatch.StartNew();
                do {
                    Accounting info;
                    Require(QueryInformationJobObject(job,1,out info,(uint)Marshal.SizeOf(typeof(Accounting)),IntPtr.Zero),"query_gui_helper_job");
                    if(info.activeProcesses==0) { State.WholeTreeEmptyConfirmed=true; return; }
                    System.Threading.Thread.Sleep(20);
                } while(clock.ElapsedMilliseconds<10000);
                throw new TimeoutException();
            });
        }
        if(State.ProcessCreated) Teardown("confirm_gui_helper_root_exit",delegate {
            uint wait=WaitForSingleObject(process.process,0);
            if(wait!=0) {
                // Contains a still-suspended root if job assignment failed.
                Require(TerminateProcess(process.process,125),"terminate_unassigned_or_stuck_gui_root");
                wait=WaitForSingleObject(process.process,10000);
            }
            if(wait==0xffffffff) throw new NativeFailure("wait_gui_helper_root_exit",Marshal.GetLastWin32Error());
            if(wait!=0) throw new TimeoutException(); State.RootExitConfirmed=true;
        });
        if(process.thread!=IntPtr.Zero) Teardown("close_gui_helper_thread",delegate { Require(CloseHandle(process.thread),"close_gui_helper_thread"); });
        if(process.process!=IntPtr.Zero) Teardown("close_gui_helper_process",delegate { Require(CloseHandle(process.process),"close_gui_helper_process"); });
        if(job!=IntPtr.Zero) Teardown("close_gui_helper_job",delegate { Require(CloseHandle(job),"close_gui_helper_job"); });
        State.TreeDisappearanceEstablished=!State.ProcessCreated ||
            (State.JobAssigned && State.JobTerminationSucceeded && State.WholeTreeEmptyConfirmed && State.RootExitConfirmed);
        if(sourceLease!=null) Teardown("release_helper_source",delegate {
            sourceLease.Dispose(); sourceLease=null; State.SourceReleaseSucceeded=true;
        });
        else State.SourceReleaseSucceeded=true;
        bool ancestorCloseFailed=false;
        for(int i=directories.Count-1;i>=0;i--) {
            IntPtr held=directories[i];
            try { Require(CloseHandle(held),"release_helper_ancestor"); }
            catch(Exception error) { ancestorCloseFailed=true; State.TeardownFailures.Add(Describe("release_helper_ancestor",error)); }
        }
        State.AncestorReleaseSucceeded=!ancestorCloseFailed;
        Teardown("verify_controller_gui_after_close",delegate {
            State.AfterClose=ReadGui(); State.CloseGuiUnchanged=Same(State.BeforeClose,State.AfterClose);
            if(State.BeforeOpen!=null && State.AfterClose.Station!=State.BeforeOpen.Station) State.CloseGuiUnchanged=false;
            if(!State.CloseGuiUnchanged) throw new InvalidOperationException();
        });
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
$guiLease = $null
$guiAttempted = $false
$guiReady = $false
$guiControl = $null
$guiDesktop = 'AttuneT2-' + $nonce + '\proof'
$report = [ordered]@{
    proposal_revision = 3
    gui_helper_sha256 = $ExpectedGuiHelperSHA256
    gui_lease_process = $null
    gui_lease_final = $null
    gui_tree_disappearance_established = $true
    gui_cleanup_succeeded = $true
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

# Pure proposal record validation. No native, account, credential or file call.
function Assert-T2ExactKeys($value, [string[]]$keys) {
    if ($value -isnot [Collections.IDictionary] -or
        @(Compare-Object -CaseSensitive @($value.Keys | Sort-Object) @($keys | Sort-Object)).Count -ne 0) { throw 'Refuse different GUI lease fields.' }
}
function Assert-T2Integer($value, [long]$minimum, [long]$maximum) {
    if (($value -isnot [int] -and $value -isnot [long]) -or $value -lt $minimum -or $value -gt $maximum) { throw 'Refuse a noninteger GUI lease value.' }
}
function Assert-T2Problem($value) {
    Assert-T2ExactKeys $value @('Stage', 'Type', 'NativeCode')
    if ($value.Stage -isnot [string] -or $value.Stage -cnotmatch '^[a-z_]{1,64}$' -or
        $value.Type -isnot [string] -or $value.Type -cnotmatch '^[A-Za-z][A-Za-z0-9]{1,63}$') { throw 'Refuse different GUI failure metadata.' }
    if ($null -ne $value.NativeCode) { Assert-T2Integer $value.NativeCode -2147483648 2147483647 }
}
function Assert-T2GuiRecord($value, [string]$nonce, [string]$controllerSid, [long]$pidExpected) {
    Assert-T2ExactKeys $value @('revision', 'nonce', 'state', 'process_sid', 'station', 'desktop', 'pid', 'gui', 'failure')
    Assert-T2Integer $value.revision 3 3
    Assert-T2Integer $value.pid 1 4294967295
    if ($value.nonce -isnot [string] -or $value.nonce -cne $nonce -or
        $value.process_sid -isnot [string] -or $value.process_sid -cne $controllerSid -or
        $value.station -isnot [string] -or $value.station -cne ('AttuneT2-' + $nonce) -or
        $value.desktop -isnot [string] -or $value.desktop -cne 'proof' -or $value.pid -ne $pidExpected -or
        $value.state -isnot [string] -or $value.state -cnotin @('ready', 'stopped', 'failed')) { throw 'Refuse changed GUI lease identity.' }
    $gui = $value.gui
    Assert-T2ExactKeys $gui @('MainThreadId', 'SetupThreadId', 'SetupThreadExited', 'HelperStationRestored', 'HelperThreadDesktopUnchanged', 'Ready', 'DesktopClosed', 'StationClosed', 'DescriptorFreed', 'PrimaryFailure', 'TeardownFailures')
    Assert-T2Integer $gui.MainThreadId 1 4294967295
    Assert-T2Integer $gui.SetupThreadId 0 4294967295
    foreach ($name in @('SetupThreadExited', 'HelperStationRestored', 'HelperThreadDesktopUnchanged', 'Ready', 'DesktopClosed', 'StationClosed', 'DescriptorFreed')) {
        if ($gui[$name] -isnot [bool]) { throw 'Refuse a nonboolean GUI lease status.' }
    }
    if ($null -ne $gui.PrimaryFailure) { Assert-T2Problem $gui.PrimaryFailure }
    if ($gui.TeardownFailures -isnot [array]) { throw 'Refuse different GUI teardown metadata.' }
    foreach ($problem in $gui.TeardownFailures) { Assert-T2Problem $problem }
    if ($null -ne $value.failure) {
        Assert-T2ExactKeys $value.failure @('stage', 'type')
        if ($value.failure.stage -cne 'gui_lease' -or $value.failure.type -isnot [string] -or
            $value.failure.type -cnotmatch '^[A-Za-z][A-Za-z0-9]{1,63}$') { throw 'Refuse different GUI lease failure metadata.' }
    }
    if ($value.state -cin @('ready', 'stopped')) {
        if ($null -ne $value.failure -or $null -ne $gui.PrimaryFailure -or $gui.TeardownFailures.Count -ne 0 -or
            -not $gui.SetupThreadExited -or -not $gui.HelperStationRestored -or -not $gui.HelperThreadDesktopUnchanged -or
            $gui.SetupThreadId -eq 0 -or $gui.MainThreadId -eq $gui.SetupThreadId) { throw 'Refuse an unestablished GUI lease.' }
        $ready = $value.state -ceq 'ready'
        if ($gui.Ready -ne $ready -or $gui.DesktopClosed -eq $ready -or
            $gui.StationClosed -eq $ready -or $gui.DescriptorFreed -eq $ready) { throw 'Refuse contradictory GUI lifetime evidence.' }
    }
}

function Read-GuiLeaseState([string]$directory) {
    $path = Join-Path $directory 'state.json'
    if (-not [IO.File]::Exists($path)) { return $null }
    $item = Get-Item -LiteralPath $path -Force
    if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or $item.Length -gt 4096) { throw 'Refuse invalid GUI lease state.' }
    $utf8 = [Text.UTF8Encoding]::new($false, $true)
    $value = [IO.File]::ReadAllText($path, $utf8) | ConvertFrom-Json -AsHashtable
    Assert-T2GuiRecord $value $nonce $controllerSid.Value $guiLease.State.Pid
    return $value
}
function Assert-GuiReady($value) {
    if ($value.state -cne 'ready') { throw 'Refuse an unestablished GUI lease.' }
}

try {
    if (-not [IO.Path]::IsPathRooted($Output)) { throw 'Evidence output must be absolute.' }
    $Output = [IO.Path]::GetFullPath($Output)
    New-Item -ItemType Directory -Path $Output | Out-Null
    # Before a disposable account exists, protect evidence/coordination from
    # birth of every later child path. Never grant that account access here.
    $controllerSid = [Security.Principal.WindowsIdentity]::GetCurrent().User
    $evidenceAcl = [Security.AccessControl.DirectorySecurity]::new()
    $evidenceAcl.SetAccessRuleProtection($true, $false)
    $evidenceAcl.SetOwner($controllerSid)
    foreach ($sid in @($controllerSid.Value, 'S-1-5-18')) {
        $identity = [Security.Principal.SecurityIdentifier]::new($sid)
        $rule = [Security.AccessControl.FileSystemAccessRule]::new($identity, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
        $evidenceAcl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $Output -AclObject $evidenceAcl
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

    # New controller/SYSTEM-only coordination, source and temp. Standard account
    # access is never granted here. Retain these synthetic records as evidence.
    $guiControl = Join-Path $Output ('gui-control-' + $nonce)
    New-Item -ItemType Directory -Path $guiControl | Out-Null
    $guiAcl = [Security.AccessControl.DirectorySecurity]::new()
    $guiAcl.SetAccessRuleProtection($true, $false)
    $guiAcl.SetOwner($controllerSid)
    foreach ($sid in @($controllerSid.Value, 'S-1-5-18')) {
        $identity = [Security.Principal.SecurityIdentifier]::new($sid)
        $rule = [Security.AccessControl.FileSystemAccessRule]::new($identity, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
        $guiAcl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $guiControl -AclObject $guiAcl
    New-Item -ItemType Directory -Path (Join-Path $guiControl 'tmp') | Out-Null
    $helperCopy = Join-Path $guiControl 'gui-helper.ps1'
    Copy-Item -LiteralPath $GuiHelper -Destination $helperCopy
    if ((Get-FileHash -LiteralPath $helperCopy -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ExpectedGuiHelperSHA256) { throw 'Refuse changed staged GUI helper source.' }
    $trustedPowerShell = Join-Path $PSHOME 'pwsh.exe'
    if (-not (Test-Path -LiteralPath $trustedPowerShell -PathType Leaf)) { throw 'Trusted PowerShell executable is missing.' }
    $guiAttempted = $true
    $report.gui_tree_disappearance_established = $false
    $report.gui_cleanup_succeeded = $false
    $guiLease = [T2GuiLeaseController]::new()
    $guiLease.Open($trustedPowerShell, $helperCopy, $ExpectedGuiHelperSHA256, $guiControl, $nonce, $createdSid, $controllerSid.Value, $env:SystemRoot)
    $report.gui_lease_process = $guiLease.State
    if ($guiLease.State.PrimaryFailure -or $guiLease.State.TeardownFailures.Count -ne 0 -or -not $guiLease.State.OpenGuiUnchanged) { throw 'GUI helper did not launch safely.' }
    $guiDeadline = [Diagnostics.Stopwatch]::StartNew()
    while (-not $guiReady) {
        $value = Read-GuiLeaseState $guiControl
        if ($value) { Assert-GuiReady $value; $guiReady = $true }
        if ($guiLease.HasExited()) { throw 'GUI helper exited before proof launch.' }
        if ($guiDeadline.Elapsed.TotalSeconds -ge 60) { throw 'GUI helper startup deadline expired.' }
        if (-not $guiReady) { Start-Sleep -Milliseconds 20 }
    }
    $proofAttempted = $true
    $proofRun = [T2StandardProcess]::Run($accountName, $createdSid, $controllerSid.Value, $password, $childPython,
        @('-I', (Join-Path $fixtureRoot 'proof.py'), '--current-standard', '--output', (Join-Path $fixtureRoot 'observations')),
        $fixtureRoot, $environment, $guiDesktop, 180000)
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
                if ($guiReady -and -not $guiLease.HasExited() -and $proofRun -and $proofRun.TreeDisappearanceEstablished -and $proofRun.TeardownFailures.Count -eq 0) {
                    if ($proofRun.ProcessCreated) {
                        try {
                            $cleanup = "import pathlib,shutil,sys; r=pathlib.Path(sys.argv[1]); p=r/'observations'; assert r.name==sys.argv[2]; p.exists() and shutil.make_archive(str(r/'artifacts'/'observations'),'zip',str(p)); p.exists() and shutil.rmtree(p)"
                            $privateCleanupRun = [T2StandardProcess]::Run($accountName, $createdSid, $controllerSid.Value, $password, (Join-Path $fixtureRoot 'runtime/Scripts/python.exe'),
                                @('-I', '-c', $cleanup, $fixtureRoot, ('AttuneT2Proof-' + $nonce)), $fixtureRoot, $environment, $guiDesktop, 60000)
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
            if ($guiAttempted) {
                if ($guiLease) {
                    try {
                        $stop = [IO.FileStream]::new((Join-Path $guiControl ('stop-' + $nonce)), [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
                        $stop.Dispose()
                    } catch { Add-CleanupIssue 'request_gui_lease_stop' $_ }
                    $guiLease.Close()
                    $report.gui_lease_process = $guiLease.State
                    $report.gui_tree_disappearance_established = $guiLease.State.TreeDisappearanceEstablished
                    $final = Read-GuiLeaseState $guiControl
                    $report.gui_lease_final = $final
                    $report.gui_cleanup_succeeded = $final -and $final.state -ceq 'stopped' -and $null -eq $final.failure -and
                        $final.gui.DesktopClosed -is [bool] -and $final.gui.DesktopClosed -and
                        $final.gui.StationClosed -is [bool] -and $final.gui.StationClosed -and
                        $final.gui.DescriptorFreed -is [bool] -and $final.gui.DescriptorFreed -and
                        $final.gui.TeardownFailures.Count -eq 0 -and $guiLease.State.PrimaryFailure -eq $null -and
                        $guiLease.State.TeardownFailures.Count -eq 0 -and $guiLease.State.OpenGuiUnchanged -and
                        $guiLease.State.CloseGuiUnchanged -and $guiLease.State.HelperSourceRetained -and
                        $guiLease.State.RetainedSourceSha256 -ceq $ExpectedGuiHelperSHA256 -and
                        $guiLease.State.SourceReleaseSucceeded -and $guiLease.State.AncestorReleaseSucceeded -and
                        $report.gui_tree_disappearance_established
                    if (-not $report.gui_cleanup_succeeded) { throw 'GUI helper cleanup is not established.' }
                } else { throw 'GUI helper invocation did not return an owned handle report.' }
            }
        } catch { Add-CleanupIssue 'gui_lease_cleanup' $_ }
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
                if ($report.private_cleanup_succeeded -and $report.proof_tree_disappearance_established -and $report.cleanup_tree_disappearance_established -and $report.gui_tree_disappearance_established -and $report.gui_cleanup_succeeded) {
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
            $report.cleanup_tree_disappearance_established -and $report.gui_tree_disappearance_established -and
            $report.gui_cleanup_succeeded -and $report.account_remove -in @('succeeded', 'already_absent') -and
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
