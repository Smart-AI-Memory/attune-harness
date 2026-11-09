# Build your first offline report on Windows

Use this quickstart to install Harness, review a plan, and produce a checked
HTML report from sample data. The practice uses fixed local commands. You need
internet access for setup, then you can finish offline without a model account.

This is a draft for Harness 1.8.0. Use the published 1.7.0 wheel for the rehearsal
below. The intended release profile is Windows 11 x64, Python 3.12, a standard
user account, and a fixed local NTFS drive. See the
[Windows support limits](supported-journeys.md#windows-capabilities-and-reliability).

## Set up a practice folder

Install Git for Windows and x64 Python 3.12 with the Python launcher. Open
Windows PowerShell 5.1 or PowerShell 7 as a standard user. Run the commands in
the same window. The commands call the virtual environment's Python directly,
so you do not need to activate it.

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

Download the source while you are still online. Clone the Harness repository
into a new folder outside the practice project:

```powershell
$Source = Join-Path $Run 'source'
git clone --depth 1 https://github.com/Smart-AI-Memory/attune-harness.git $Source
```

If you already have a checkout that contains this guide, set `$Source` to its
full path instead. Then prepare a new practice project:

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
The practice copy writes UTF-8 text with LF line endings so the exact output
checks work in both Windows shells.
The task and request live outside that checkout. Preparation leaves the plan
unaccepted.

## Review and approve the plan

```powershell
& $Python -I -m attune_harness plan --request $Request --project $Project --config $Registry --task-dir $Task
```

Expect `draft`, no missing questions, and a `checkpoint_digest`. Read the goal,
participants, and checks. The plan allows a change to `report.py` and protects
the data, expected results, tests, pytest configuration, and participant
registry. Stop if the displayed scope differs.

Copy the full `checkpoint_digest` from the preview. Then approve that scope:

```powershell
$Checkpoint = Read-Host 'Paste the full checkpoint_digest from your draft'
& $Python -I -m attune_harness plan --task-dir $Task --accept --checkpoint $Checkpoint
```

Expect `accepted`. The build is a separate decision.

## Build and check the report

Review the two local participants in `$Registry`. The fixed worker changes one
line in `report.py`, and the fixed reviewer supplies a protocol response. The
protected tests check the result. `--allow-external` allows these local command
participants to run.

```powershell
& $Python -I -m attune_harness build $Task --allow-external
& $Python -I -m attune_harness status $Task --format markdown
git -C $Project diff --name-only
```

Expect `completed`, passing task and final checks, and only `report.py` in the
diff. If the build fails or its effects are uncertain, read the saved status
before taking any recovery action.

Write the HTML report outside the project, then open it:

```powershell
$Report = Join-Path $Practice 'activity-report.html'
& $Python (Join-Path $Project 'report.py') (Join-Path $Project 'data\activity.csv') --format html --output $Report
Invoke-Item -LiteralPath $Report
```

Check for **6 entries** and **270 minutes**. Compare the project totals and date
range with the CSV. To try again, prepare a new practice directory.
