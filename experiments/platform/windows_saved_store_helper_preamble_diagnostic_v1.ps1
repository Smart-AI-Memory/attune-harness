# Zero-account, no-GUI startup diagnostic. The original helper stays unchanged.
[CmdletBinding()]
param(
    [string]$Helper,
    [string]$Output,
    [switch]$DiagnosticChild,
    [ValidateSet('forced_failure','preamble_refusal','preamble_actual')][string]$Case,
    [string]$Preamble,
    [string]$ControlDirectory,
    [string]$Nonce,
    [string]$CanonicalSid
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$helperHash = 'cf85ed8835e1bea8eee6d8bb86c2b6ce0eadd05c763f38bd2ff7f6f8be40e5fd'
$prefixHash = '34453c9ab5d3079ea511db8131daa738c637c4b455adf2c027537bafafad3169'
if ($DiagnosticChild) {
    $exitCode = 47
    try {
        $names = @([Environment]::GetEnvironmentVariables().Keys | ForEach-Object { [string]$_ } | Sort-Object)
        [Console]::Out.WriteLine(([ordered]@{ event = 'startup'; environment_key_names = $names } | ConvertTo-Json -Compress))
        if ($Case -ceq 'forced_failure') {
            [Console]::Error.WriteLine('t2_deliberate_stderr')
            throw [InvalidOperationException]::new('t2_deliberate_failure')
        }
        if ((Get-FileHash -LiteralPath $Preamble -Algorithm SHA256).Hash.ToLowerInvariant() -cne $prefixHash) { throw 'Refuse changed preamble.' }
        $argumentNonce = $(if ($Case -ceq 'preamble_refusal') { 'invalid-nonce' } else { $Nonce })
        & $Preamble -StartReviewedGuiLease -ControlDirectory $ControlDirectory -Nonce $argumentNonce -UserSid $CanonicalSid -ControllerSid $CanonicalSid
        [Console]::Out.WriteLine('{"event":"preamble_passed"}')
        $exitCode = 0
    } catch {
        # Fixed fields only: no error message, invocation text or environment values.
        [Console]::Out.WriteLine(([ordered]@{ event = 'typed_failure'; type = $_.Exception.GetType().FullName; script_line = $_.InvocationInfo.ScriptLineNumber } | ConvertTo-Json -Compress))
    }
    [Environment]::Exit($exitCode)
}

if (-not $Helper -or -not $Output) { throw 'Helper and fresh output are required.' }
if ((Get-FileHash -LiteralPath $Helper -Algorithm SHA256).Hash.ToLowerInvariant() -cne $helperHash) { throw 'Refuse changed original helper.' }
$raw = [IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $Helper).Path)
$source = [Text.Encoding]::UTF8.GetString($raw)
$boundary = $source.IndexOf("Add-Type -TypeDefinition @'`n", [StringComparison]::Ordinal)
if ($boundary -lt 0) { throw 'Refuse missing literal native boundary.' }
$prefix = $source.Substring(0, $boundary)
$prefixBytes = [Text.Encoding]::UTF8.GetBytes($prefix)
$observedPrefixHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($prefixBytes)).ToLowerInvariant()
if ($observedPrefixHash -cne $prefixHash) { throw 'Refuse changed preamble boundary.' }
$tokens = $null; $parseErrors = $null
$null = [Management.Automation.Language.Parser]::ParseInput($prefix, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -ne 0) { throw 'Refuse malformed exact preamble.' }
$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User
$system = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
if ($sid.Value -ceq $system.Value) { throw 'Refuse a SYSTEM controller for this diagnostic.' }
function New-PrivateDiagnosticDirectory([string]$path) {
    if (Test-Path -LiteralPath $path) { throw 'Refuse an existing diagnostic directory.' }
    $null = New-Item -ItemType Directory -Path $path
    $acl = [Security.AccessControl.DirectorySecurity]::new()
    $acl.SetAccessRuleProtection($true, $false)
    $acl.SetOwner($sid)
    foreach ($identity in @($sid, $system)) {
        $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($identity, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow'))
    }
    Set-Acl -LiteralPath $path -AclObject $acl
}
New-PrivateDiagnosticDirectory $Output
$nonceValue = [Guid]::NewGuid().ToString('N')
$control = Join-Path $Output ('gui-control-' + $nonceValue)
New-PrivateDiagnosticDirectory $control
$temp = Join-Path $control 'tmp'
$null = New-Item -ItemType Directory -Path $temp
$prefixPath = Join-Path $Output 'exact-helper-preamble.ps1'
[IO.File]::WriteAllBytes($prefixPath, $prefixBytes)

# Managed process/pipe operations only. No WinAPI, account, GUI or storage proof.
Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading.Tasks;
public static class T2PreambleCaptureV1 {
    public sealed class StreamResult { public string Text; public long DiscardedCharacters; }
    public sealed class Result {
        public int ExitCode; public bool TimedOut, KillTreeRequested;
        public StreamResult Stdout, Stderr;
    }
    static StreamResult Drain(StreamReader reader) {
        var kept=new StringBuilder(); long discarded=0; var buffer=new char[1024]; int count;
        while((count=reader.Read(buffer,0,buffer.Length))!=0) {
            int take=Math.Min(count,8192-kept.Length);
            if(take>0) kept.Append(buffer,0,take);
            discarded+=count-take;
        }
        return new StreamResult{Text=kept.ToString(),DiscardedCharacters=discarded};
    }
    public static Result Run(string executable,string[] argv,string root,string systemRoot,string temp) {
        var start=new ProcessStartInfo(executable){UseShellExecute=false,CreateNoWindow=true,
            RedirectStandardInput=true,RedirectStandardOutput=true,RedirectStandardError=true,WorkingDirectory=root};
        foreach(var arg in argv) start.ArgumentList.Add(arg);
        start.Environment.Clear();
        start.Environment["SystemRoot"]=systemRoot; start.Environment["TEMP"]=temp; start.Environment["TMP"]=temp;
        var result=new Result();
        using(var process=new Process{StartInfo=start}) {
            if(!process.Start()) throw new InvalidOperationException("process_start_false");
            process.StandardInput.Close();
            var stdout=Task.Run(()=>Drain(process.StandardOutput));
            var stderr=Task.Run(()=>Drain(process.StandardError));
            try {
                if(!process.WaitForExit(30000)) {
                    result.TimedOut=true; result.KillTreeRequested=true; process.Kill(true);
                    if(!process.WaitForExit(5000)) throw new TimeoutException("child_root_exit_unconfirmed");
                }
                if(!Task.WaitAll(new Task[]{stdout,stderr},5000)) throw new TimeoutException("stream_drain_unconfirmed");
                result.ExitCode=process.ExitCode; result.Stdout=stdout.Result; result.Stderr=stderr.Result;
                return result;
            } finally {
                if(!process.HasExited) { result.KillTreeRequested=true; process.Kill(true); process.WaitForExit(5000); }
            }
        }
    }
}
'@
$report = [ordered]@{
    status = 'startup_diagnostic_incomplete'; helper_sha256 = $helperHash; preamble_sha256 = $prefixHash
    executable = (Join-Path $PSHOME 'pwsh.exe'); powershell = $PSVersionTable.PSVersion.ToString()
    supplied_environment_key_names = @('SystemRoot', 'TEMP', 'TMP')
    same_current_sid_for_both_parameters = $true; cases = @(); failure = $null
    account_fixture_invoked = $false; accounts_or_credentials_created = $false; gui_objects_created = $false
    native_helper_constructed = $false; storage_witness_invoked = $false
    t2_d3_gate = 'unpassed'; production_port_allowed = $false
}
try {
    foreach ($caseName in @('forced_failure', 'preamble_refusal', 'preamble_actual')) {
        $childArgv = @('-NoLogo','-NoProfile','-NonInteractive','-File',$PSCommandPath,'-DiagnosticChild','-Case',$caseName,
            '-Preamble',$prefixPath,'-ControlDirectory',$control,'-Nonce',$nonceValue,'-CanonicalSid',$sid.Value)
        $result = [T2PreambleCaptureV1]::Run($report.executable, $childArgv, $control, $env:SystemRoot, $temp)
        $row = [ordered]@{ case = $caseName; capture = $result; events = $null }
        $report.cases += $row
        $events = @($result.Stdout.Text -split '\r?\n' | Where-Object { $_ } | ForEach-Object { $_ | ConvertFrom-Json -AsHashtable })
        $row.events = $events
        # Prove both-stream capture before executing any helper preamble.
        if ($result.TimedOut -or $result.Stdout.DiscardedCharacters -ne 0 -or $result.Stderr.DiscardedCharacters -ne 0) { throw 'Incomplete bounded child capture.' }
        if ($caseName -ceq 'forced_failure') {
            if ($result.ExitCode -ne 47 -or $result.Stderr.Text.Trim() -cne 't2_deliberate_stderr' -or
                $events.Count -ne 2 -or $events[0].event -cne 'startup' -or $events[1].event -cne 'typed_failure' -or
                $events[1].type -cne 'System.InvalidOperationException') { throw 'Deliberate failing child was not captured.' }
        } elseif ($caseName -ceq 'preamble_refusal') {
            if ($result.ExitCode -ne 47 -or $events.Count -ne 2 -or $events[1].event -cne 'typed_failure' -or
                $events[1].type -cne 'System.Management.Automation.RuntimeException' -or $events[1].script_line -ne 15) { throw 'Exact invalid-nonce preamble control did not refuse.' }
        } else {
            if ($events.Count -ne 2 -or $events[0].event -cne 'startup' -or
                ($result.ExitCode -eq 0 -and $events[1].event -cne 'preamble_passed') -or
                ($result.ExitCode -eq 47 -and $events[1].event -cne 'typed_failure') -or
                ($result.ExitCode -ne 0 -and $result.ExitCode -ne 47)) { throw 'Actual preamble outcome was not captured.' }
            $report.actual_preamble_outcome = $(if ($result.ExitCode -eq 0) { 'passed' } else { 'refused_with_typed_error' })
        }
    }
    $report.status = 'startup_diagnostic_completed'
} catch {
    $report.failure = [ordered]@{ type = $_.Exception.GetType().FullName }
} finally {
    $report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $Output 'diagnostic.json') -Encoding utf8
}
if ($report.status -cne 'startup_diagnostic_completed') { throw 'Startup diagnostic control failed; inspect retained typed records.' }
