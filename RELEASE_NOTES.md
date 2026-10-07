# v1.5.2

The website's relay records now show team members and results with proper line breaks. All 61 club-record pages were checked, and affected rows in seven pages were repaired. Expanding image galleries now moves the footer below the expanded content.

The editor preserves relay teams when loading and saving records. Saves use atomic replacement; sponsor categories use a recoverable batch transaction. Draft guards protect unsaved edits during navigation, reload and closing. Imported assets use unique names and unused imports are removed safely when an edit is discarded.

Additional corrections cover calendar and download row identities, malformed input, text and sponsor markup preservation, failed modal saves, trainer ordering and media format handling. Git publication restores local work after failed pulls, retains conflict recovery information and consistently excludes release metadata from website-edit commits.

Validation: 49 automated tests passed, including two round trips of every club-record page, hidden Tk checks, save-recovery failures and Git operations against temporary repositories. The compiled executable initialized all 12 tabs and loaded image/PDF dependencies successfully.

The GitHub release tag is `v1.5.2`; the application and Windows file version are `1.5.2.0`.

## Windows build

Use Python 3.11 with Tk support, Git and a clean virtual environment. Run from the repository root:

```powershell
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements-editor.txt
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean ThibertaWebsiteEditor.spec
```

The output is `dist/ThibertaWebsiteEditor.exe`. Place it in the website checkout before running; website paths are resolved relative to the executable's directory. Keep a copy of the previous executable before replacing it. For a startup check that avoids network operations and visible windows:

```powershell
$smokeOutput = Join-Path $env:TEMP 'ThibertaWebsiteEditor-smoke.json'
$editorProcess = Start-Process -FilePath (Join-Path (Get-Location).Path 'ThibertaWebsiteEditor.exe') -ArgumentList @('--smoke-test-output', $smokeOutput) -WindowStyle Hidden -Wait -PassThru
Get-Content -LiteralPath $smokeOutput
$editorProcess.ExitCode
```
