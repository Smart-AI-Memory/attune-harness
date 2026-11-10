# Build your first offline report on Windows

Use this quickstart to install Harness, review a plan, and produce a checked
HTML report from sample data. The practice uses fixed local commands. You need
internet access for setup, then you can finish offline without a model account.

This draft rehearses a proposed Harness 1.8.0 journey with the published 1.7.0
wheel. The rehearsal ran on Windows 11 ARM64 with emulated x64 Python 3.12.10
and Windows PowerShell 5.1, using a standard user account and a fixed local
NTFS drive. It checked the generated HTML bytes. Qualification still requires
the 1.8.0 candidate wheel on native Windows 11 x64 in Windows PowerShell 5.1
and PowerShell 7, including opening and inspecting the report in a desktop
browser. See the [Windows support limits](supported-journeys.md#windows-capabilities-and-reliability).

## Set up a practice folder

Install Git for Windows and x64 Python 3.12 with the Python launcher. Open
Windows PowerShell 5.1 as a standard user for the rehearsal. Use a fresh shell
without Git environment overrides such as `GIT_DIR`, `GIT_WORK_TREE`, or
`GIT_INDEX_FILE`. Run the commands in the same window. The commands call the
virtual environment's Python directly, so you do not need to activate it.

List the installed interpreters and choose the full path to x64 Python 3.12:

```powershell
py -0p
$BasePython = Read-Host 'Enter the full path to x64 Python 3.12'
$Profile = & $BasePython -c 'import sys, sysconfig; print(sys.version_info[:2], sysconfig.get_platform())'
if ($LASTEXITCODE -ne 0 -or $Profile -ne '(3, 12) win-amd64') { throw 'Choose x64 Python 3.12.' }
```

Choose a new folder on a fixed local NTFS drive. This example uses a folder
under your local application data directory. If the folder already exists,
choose another name.

```powershell
$Run = Join-Path $env:LOCALAPPDATA 'Harness offline report'
New-Item -ItemType Directory -Path $Run -ErrorAction Stop
& $BasePython -m venv (Join-Path $Run 'venv')
$Python = Join-Path $Run 'venv\Scripts\python.exe'
& $Python -m pip install 'attune-harness==1.7.0' 'pytest==9.1.1'
& $Python -m pip show attune-harness
$env:ATTUNE_USAGE_PING = '0'
$env:ATTUNE_VERSION_CHECK = '0'
```

Expect `Version: 1.7.0`. Stop if a command reports an error.

Download the source while you are still online. If you already have a checkout
that contains this guide, set `$Source` to its full path. For a guide in a pull
request, use a checkout of the reviewed revision. Once the guide is on
`main`, you can clone it into a new folder outside the practice project:

```powershell
$Source = Join-Path $Run 'source'
git clone --depth 1 https://github.com/Smart-AI-Memory/attune-harness.git $Source
```

Prepare a new practice project:

```powershell
$Practice = Join-Path $Run 'practice'
& $Python -I (Join-Path $Source 'examples\windows-offline-report\prepare.py') $Practice
$Project = Join-Path $Practice 'project'
$Task = Join-Path $Practice 'task'
$Request = Join-Path $Practice 'task.work.json'
$Registry = Join-Path $Project 'participants.json'
```

The helper creates a disposable Git project with an unfinished `report.py`,
the sample CSV, expected results, two test files, and a participant registry.
The practice copy uses UTF-8 text with LF line endings for the exact output
checks.
The task and request live outside that checkout. Preparation leaves the plan
unaccepted.

## Review and approve the plan

```powershell
& $Python -I -m attune_harness plan --request $Request --project $Project --config $Registry --task-dir $Task
```

Expect `"status": "draft"`, an empty `missing` list, and a
`checkpoint_digest`. Read the goal, scope, and checks in the preview. Open
`$Registry` to inspect the two local participants and `$Request` to inspect
the `effects` field. The only allowed change is to `report.py`. The protected
files include the data, expected results, tests, pytest configuration, and
participant registry. Stop if the preview or request differs.

Copy the full `checkpoint_digest` from the preview. Then approve that scope:

```powershell
$Checkpoint = Read-Host 'Paste the full checkpoint_digest from your draft'
& $Python -I -m attune_harness plan --task-dir $Task --accept --checkpoint $Checkpoint
```

Expect `accepted`. The build is a separate decision.

## Build and check the report

The fixed worker changes one line in `report.py`. The fixed reviewer
supplies a sample response. The protected tests check the result.
`--allow-external` allows these local command participants to run.

```powershell
& $Python -I -m attune_harness build $Task --allow-external
& $Python -I -m attune_harness status $Task --format markdown
git -C $Project status --porcelain=v1 --untracked-files=all
```

Expect `completed`, passing task and final checks, and a single Git status
line, ` M report.py`, with a leading space. If the build fails or its effects
are uncertain, read the saved status before taking any recovery action.

Write the HTML report outside the project, then open it:

```powershell
$Report = Join-Path $Practice 'activity-report.html'
& $Python (Join-Path $Project 'report.py') (Join-Path $Project 'data\activity.csv') --format html --output $Report
Invoke-Item -LiteralPath $Report
```

If `Invoke-Item` opens a different application, open the HTML file directly in
a desktop browser. Check for **6 entries** and **270 minutes**. Compare the
project totals and date range with the CSV. To try again, prepare a new
practice directory.
