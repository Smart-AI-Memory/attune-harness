# Additive normalization diagnostic. No account, GUI construction or storage proof.
[CmdletBinding()]
param(
    [string]$Helper,
    [string]$Output,
    [switch]$DiagnosticChild,
    [ValidateSet('forced_failure','preamble_refusal','unexpected_key','preamble_actual','compile_helper_csharp')][string]$Case,
    [string]$Preamble,
    [string]$ControlDirectory,
    [string]$Nonce,
    [string]$CanonicalSid
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$helperHash = '5786e2eefbb6e61f65ef4caaf17a4668ad7dd14ae8f552d72dffcc21845729bf'
$prefixHash = 'f9672a8b74c739f22f96be6ba5e9e3671cd513bf505109225132902e017f72f4'
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
        if ($Case -ceq 'unexpected_key') { [Environment]::SetEnvironmentVariable('T2_UNEXPECTED_KEY', 'synthetic', [EnvironmentVariableTarget]::Process) }
        $argumentNonce = $(if ($Case -ceq 'preamble_refusal') { 'invalid-nonce' } else { $Nonce })
        & $Preamble -StartReviewedGuiLease -ControlDirectory $ControlDirectory -Nonce $argumentNonce -UserSid $CanonicalSid -ControllerSid $CanonicalSid
        [Console]::Out.WriteLine('{"event":"preamble_passed"}')
        if ($Case -ceq 'compile_helper_csharp') {
            # Parse/hash the same in-memory bytes. Never invoke the full helper.
            $fullBytes = [IO.File]::ReadAllBytes($Helper)
            $observedFullHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($fullBytes)).ToLowerInvariant()
            if ($observedFullHash -cne $helperHash) { throw 'Refuse changed compilation source.' }
            $parseTokens = $null; $parseErrors = $null
            $ast = [Management.Automation.Language.Parser]::ParseInput([Text.Encoding]::UTF8.GetString($fullBytes), [ref]$parseTokens, [ref]$parseErrors)
            if ($parseErrors.Count -ne 0) { throw 'Refuse malformed compilation source.' }
            $nodes = @($ast.FindAll({ param($node)
                $node -is [Management.Automation.Language.CommandAst] -and $node.GetCommandName() -ceq 'Add-Type'
            }, $true))
            if ($nodes.Count -ne 1) { throw 'Refuse different C# block count.' }
            $elements = $nodes[0].CommandElements
            if ($elements.Count -ne 3 -or $elements[1] -isnot [Management.Automation.Language.CommandParameterAst] -or
                $elements[1].ParameterName -cne 'TypeDefinition' -or $elements[2] -isnot [Management.Automation.Language.StringConstantExpressionAst] -or
                $elements[2].StringConstantType.ToString() -cne 'SingleQuotedHereString') { throw 'Refuse executable C# extraction.' }
            $code = $elements[2].Value
            $codeHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($code))).ToLowerInvariant()
            if ($codeHash -cne '7b6e8e92cf3ced6483b44fb64d39af039bd32486ccaa48f1a66ab66e461563a0' -or
                $code -match 'ModuleInitializer' -or $code -match 'static\s+T2PrivateGuiLease\s*\(' -or ('T2PrivateGuiLease' -as [type])) { throw 'Refuse changed, initialized or previously loaded GUI type.' }
            # Exercise Add-Type AFTER normalization, without calling any GUI constructor/method.
            $compiled = @(Microsoft.PowerShell.Utility\Add-Type -TypeDefinition $code -Language CSharp -PassThru -ErrorAction Stop)
            if (-not ($compiled | Where-Object { $_.FullName -ceq 'T2PrivateGuiLease' })) { throw 'Expected helper type was not compiled.' }
            [Console]::Out.WriteLine(([ordered]@{ event = 'helper_csharp_compiled'; csharp_sha256 = $codeHash; gui_constructor_invoked = $false; native_methods_invoked = $false } | ConvertTo-Json -Compress))
        }
        $exitCode = 0
    } catch {
        # Fixed fields only: no error message, invocation text or environment values.
        [Console]::Out.WriteLine(([ordered]@{ event = 'typed_failure'; type = $_.Exception.GetType().FullName; script_line = $_.InvocationInfo.ScriptLineNumber } | ConvertTo-Json -Compress))
    }
    if ($Case -cin @('unexpected_key','preamble_actual','compile_helper_csharp')) {
        $afterNames = @([Environment]::GetEnvironmentVariables().Keys | ForEach-Object { [string]$_ } | Sort-Object)
        [Console]::Out.WriteLine(([ordered]@{ event = 'environment_after_prefix'; environment_key_names = $afterNames } | ConvertTo-Json -Compress))
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
    native_helper_constructed = $false; storage_witness_invoked = $false; helper_csharp_compile_only = $true
    t2_d3_gate = 'unpassed'; production_port_allowed = $false
}
try {
    foreach ($caseName in @('forced_failure', 'preamble_refusal', 'unexpected_key', 'preamble_actual', 'compile_helper_csharp')) {
        $childArgv = @('-NoLogo','-NoProfile','-NonInteractive','-File',$PSCommandPath,'-DiagnosticChild','-Case',$caseName,
            '-Preamble',$prefixPath,'-Helper',$Helper,'-ControlDirectory',$control,'-Nonce',$nonceValue,'-CanonicalSid',$sid.Value)
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
        } elseif ($caseName -ceq 'unexpected_key') {
            if ($result.ExitCode -ne 47 -or $events.Count -ne 3 -or $events[1].event -cne 'typed_failure' -or
                $events[1].type -cne 'System.Management.Automation.RuntimeException' -or $events[1].script_line -ne 41 -or
                $events[2].event -cne 'environment_after_prefix' -or $events[2].environment_key_names -cnotcontains 'T2_UNEXPECTED_KEY') { throw 'Unknown environment-key control was not refused at the unchanged guard.' }
        } else {
            $expectedCount = $(if ($caseName -ceq 'compile_helper_csharp') { 4 } else { 3 })
            if ($result.ExitCode -ne 0 -or $events.Count -ne $expectedCount -or $events[0].event -cne 'startup' -or
                $events[1].event -cne 'preamble_passed') { throw 'Normalized exact preamble did not pass.' }
            if ($caseName -ceq 'compile_helper_csharp') {
                if ($events[2].event -cne 'helper_csharp_compiled' -or $events[2].csharp_sha256 -cne '7b6e8e92cf3ced6483b44fb64d39af039bd32486ccaa48f1a66ab66e461563a0' -or
                    $events[2].gui_constructor_invoked -cne $false -or $events[2].native_methods_invoked -cne $false) { throw 'Normalized helper C# compilation was not established.' }
            }
            $report.actual_preamble_outcome = 'passed_after_process_local_search_path_removal'
        }
        if ($caseName -cin @('unexpected_key','preamble_actual','compile_helper_csharp')) {
            $last = $events[-1]
            if ($last.event -cne 'environment_after_prefix' -or $last.environment_key_names -icontains 'PATH' -or
                $last.environment_key_names -icontains 'PATHEXT') { throw 'Process-local search variables were not absent after the control.' }
        }
    }
    $report.status = 'startup_diagnostic_completed'
} catch {
    $report.failure = [ordered]@{ type = $_.Exception.GetType().FullName }
} finally {
    $report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $Output 'diagnostic.json') -Encoding utf8
}
if ($report.status -cne 'startup_diagnostic_completed') { throw 'Startup diagnostic control failed; inspect retained typed records.' }
