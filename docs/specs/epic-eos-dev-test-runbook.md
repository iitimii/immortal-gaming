# Epic EOS Dev Test Runbook

This document records the dev hands-on test flow for Epic EOS Metrics. The goal is to make it easy to judge in a single test run:

1. Whether the package was correctly uploaded to the Epic dev artifact.
2. Whether the EOS helper successfully reported the Metrics session.
4. On failure, which log to check first and how to fix it.

## Current Test Goals

This phase only validates EOS Metrics:

1. `BeginPlayerSession` is called when the game starts.
2. `EndPlayerSession` is called when the game exits.
3. The Epic backend shows player session / online user related data.

This phase does not validate:

1. Achievements.
2. Friends, Presence, Overlay.
3. Lobby, P2P, cloud saves.
4. In-game Epic login UI.

## Prerequisites

The following must already be prepared locally:

1. `E:\tools\dotnet` is available, and `dotnet --info` works.
2. The EOS SDK is extracted to `E:\SDK\EOS`.
3. The BuildPatchTool path has been written to `tools/package/epic/epic_config.env`.
4. The EOS runtime config has been written to `tools/package/epic/eos_runtime.env`.
5. `tools/package/epic/eos_runtime.env` and `tools/package/epic/epic_config.env` must not be committed to git.
6. `EPIC_EOS_SANDBOX_ID` may be left empty. When the Epic Games Launcher starts a store package it passes
   the sandbox argument, which overrides the packaged fallback before Electron starts the helper.

For dev testing, the Epic artifact must be bound to the dev deployment. Do not use the live deployment to test the dev artifact.
The official Epic publish script defaults to the Live deployment, so dev test commands must explicitly include
`-EosEnv dev`.

## Important Rule: BuildVersion Must Be Unique

Epic's BuildPatchTool does not allow the same `BuildVersion` to be uploaded twice to the same artifact.

If you see:

```text
Build already exists.
The artifact ... already has a binary registered with version v3.8.0-desktop.
Please ensure the provided BuildVersion argument is unique for each upload.
```

This is neither an EOS failure nor a broken package. It only means this version number has already been uploaded.

Fix: pass a new `-BuildVersion` for every dev upload.

Recommended format:

```powershell
$buildVersion = "v3.8.0-eos-dev-$(Get-Date -Format yyyyMMdd-HHmmss)"
powershell ./tools/package/publish_epic.ps1 -BuildVersion $buildVersion -RequireEosRuntime -RequireUpload -EosEnv dev -SkipNpmInstall
```

If you are testing an official new version, you can also use the official version number plus a test suffix:

```powershell
$buildVersion = "v3.8.1-eos-dev-$(Get-Date -Format yyyyMMdd-HHmmss)"
powershell ./tools/package/publish_epic.ps1 -BuildVersion $buildVersion -RequireEosRuntime -RequireUpload -EosEnv dev
```

When BuildPatchTool reports that it is not the latest version:

```text
You are not using the latest version of BuildPatchTool.
```

This is usually just a warning. As long as no non-zero exit code follows and the upload succeeds, it does not block the current EOS test. You can download the latest BuildPatchTool and replace it later.

## Dev Test Steps

### 1. Publish the helper locally first

```powershell
$env:DOTNET_ROOT = "E:\tools\dotnet"
$env:Path = "E:\tools\dotnet;$env:Path"
dotnet publish .\desktop-eos-helper\desktop-eos-helper.csproj -c Release -r win-x64 --self-contained true -o .\desktop-eos-helper\publish\win-x64
```

Success criteria:

1. The command exit code is 0.
2. `desktop-eos-helper\publish\win-x64\eos-helper.exe` exists.
3. `desktop-eos-helper\publish\win-x64\EOSSDK-Win64-Shipping.dll` exists.

The C# wrapper bundled with the EOS SDK may emit many nullable warnings. As long as publish succeeds, these warnings do not block testing.

### 2. Do a preview package first

```powershell
$buildVersion = "v3.8.0-eos-dev-$(Get-Date -Format yyyyMMdd-HHmmss)"
powershell ./tools/package/publish_epic.ps1 -BuildVersion $buildVersion -Preview -RequireEosRuntime -EosEnv dev -SkipNpmInstall
```

Success criteria:

1. Outputs `[OK] Prepared Epic EOS runtime config and helper.`.
2. Outputs `[Preview] Epic upload was not executed.`.
3. The `win-unpacked` directory pointed to by `tmp\desktop_content_root.txt` exists.
4. `win-unpacked\resources\eos-helper\eos-helper.exe` exists.
5. `win-unpacked\resources\eos-runtime.json` exists.

Do not open or print the contents of `eos-runtime.json`, because it may contain the runtime client secret.

### 3. Upload the dev artifact

Generate a new unique `BuildVersion` for every upload:

```powershell
$buildVersion = "v3.8.0-eos-dev-$(Get-Date -Format yyyyMMdd-HHmmss)"
powershell ./tools/package/publish_epic.ps1 -BuildVersion $buildVersion -RequireEosRuntime -RequireUpload -EosEnv dev -SkipNpmInstall
```

Success criteria:

1. BuildPatchTool exit code is 0.
2. The script outputs `[Success] Uploaded this build to Epic.`.
3. The new build version is visible on the artifact in the Epic backend.

Failure criteria:

1. `Build already exists`: duplicate version number; re-upload with a new `-BuildVersion`.
2. `BuildPatchTool failed with exit code ...`: the upload tool failed; first check `C:\Users\wangx\AppData\Local\BuildPatchTool\Saved\Logs\BuildPatchTool.log`.
3. Missing secret prompt: check whether the environment variable named by `EPIC_CLIENT_SECRET_ENV_VAR` in `tools/package/epic/epic_config.env` has a value, or enter it manually when prompted.

### 4. Install and launch from the Epic Launcher

Launching through the Epic Launcher is recommended to make sure you are testing the actual store package. The anonymous Metrics
path does not depend on Epic Account Auth, so the locally packaged exe can also be used for helper smoke tests.

Success criteria:

1. The Epic Launcher can install or update to the build version just uploaded.
2. After clicking launch in the Launcher, the game opens normally.
3. The game does not exit because of an EOS failure.

### 5. Check local logs

Log directory:

```text
%LOCALAPPDATA%\CultivationWorldSimulator\logs\electron
```

Focus on three files:

```text
telemetry.log
eos-helper.stdout.log
eos-helper.stderr.log
```

On success you should normally see:

```json
{"type":"status","state":"session_active"}
```

After exiting the game you should also see:

```json
{"type":"status","state":"session_ended"}
```

If you only see `session_active` but not `session_ended`, first confirm whether the game exited normally. Killing the process abnormally may not leave time to report end session.

### 6. Check Metrics in the Epic backend

Epic backend metrics may not refresh in real time. For dev testing it is recommended to:

1. Stay in the game for 2 to 5 minutes after launching.
2. Close the game normally.
3. Wait a few minutes, then check the Metrics / player sessions / online users related pages.

Success criteria:

1. Player session data appears for the corresponding build/deployment in the backend.
2. Online or session statistics change for the same time window.

Failure criteria:

1. Local logs already show `session_active`, but the backend shows nothing shortly after: wait a while first; do not immediately declare failure.
2. Still no data after a long time: check whether the dev artifact is bound to the dev deployment, and whether the `-EosEnv dev` used for the package is correct.

## Common Failures and Handling

### `eos_initialize_failed`

Meaning: EOS SDK initialization failed.

Handling:

1. Confirm that `resources\eos-helper\EOSSDK-Win64-Shipping.dll` exists.
2. Confirm that `resources\eos-helper\xaudio2_9redist.dll` exists.
3. Check EOS's own logs in `eos-helper.stderr.log`.

### `eos_platform_create_failed`

Meaning: EOS Platform creation failed.

Common causes:

1. Product ID, Sandbox ID, Deployment ID, Client ID, or Client Secret is wrong.
2. The dev artifact and deployment do not match.
3. `eos-runtime.json` was not included during packaging.

Handling:

1. Check `tools/package/epic/eos_runtime.env`; do not print the secret.
2. Use `-Preview -RequireEosRuntime -EosEnv dev` to reconfirm that the in-package resources exist.
3. Confirm that the dev artifact is bound to the dev deployment.

### `eos_metrics_begin_failed`

Meaning: the EOS Platform was created, but Metrics BeginPlayerSession failed.

Handling:

1. Check the EOS result in `eos-helper.stderr.log`.
2. Confirm that the policy allows Metrics.
3. Confirm that Product / Sandbox / Deployment / Artifact all belong to the same dev chain.

### Game starts, but there are no EOS logs

Meaning: Electron did not enable the Epic telemetry provider, or the helper was not packaged.

Handling:

1. Confirm this is an Epic distribution package, not a generic/GitHub package.
2. Confirm that `resources\desktop-distribution.json` exists.
3. Confirm that `resources\eos-helper\eos-helper.exe` exists.
4. Confirm that the packaging command includes `-RequireEosRuntime`.

## Test the Official New Version After Dev Testing

Recommended flow:

1. First test EOS on the dev artifact with a unique `BuildVersion`.
2. Confirm success in both the dev logs and backend Metrics.
3. Then release a new official version number, for example `v3.8.1`.
4. Build the official Epic package with the new tag / new version number.
5. For live testing use `-EosEnv live`, and confirm that the live artifact is bound to the live deployment.

Live upload example:

```powershell
$buildVersion = "v3.8.1-desktop"
powershell ./tools/package/publish_epic.ps1 -BuildVersion $buildVersion -RequireEosRuntime -RequireUpload -EosEnv live
```

If the same live version number has already been uploaded, do not overwrite it; use a new official version number or add a revision suffix.

## Conclusion Record Template

A successful dev test can be recorded like this:

```text
Epic EOS dev test passed.
BuildVersion: <actual uploaded version>
Local helper session_active: OK
Local helper session_ended: OK
Epic backend Metrics visible: OK
```

A failed dev test can be recorded like this:

```text
Epic EOS dev test failed.
BuildVersion: <actual uploaded version>
Local helper state: <state from stdout>
Local helper detail: <detail from stdout, without secrets>
stderr key result: <EOS result>
Next action: <handle per the matching failure item in this document>
```
