When the user invokes this command, run the GitHub build, compression, and release flow:

1. **Build, compress, and publish the GitHub Release**:
   Run `powershell ./tools/package/publish_github.ps1` and wait for it to complete successfully.
   The script runs `pack_github.ps1`, `compress.ps1`, and `release.ps1` in order.
   If the local zip already exists and you only want to retry publishing, manually run `powershell ./tools/package/publish_github.ps1 -NoBuild`.
   To only preview the zip that would be uploaded without calling the GitHub API, manually run `powershell ./tools/package/publish_github.ps1 -Preview`.

Note: if any step fails (non-zero exit code), stop immediately and report the error to the user.
