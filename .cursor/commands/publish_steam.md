When the user invokes this command, run the desktop Electron build and publish it to Steam.

Steam is currently kept as an available publish target; it reuses the shared desktop content root and no longer has its own desktop build pipeline.

1. **Build, package, and publish to Steam**:
   Run `powershell ./tools/package/publish_steam.ps1` and wait for it to finish.
   The script automatically runs `pack_desktop.ps1`, reads `tmp/desktop_content_root.txt`, then calls `steam/publish.ps1 -ContentRoot ... -BuildDesc <current git tag>-desktop`.
   The upload stage may require the user to manually enter the Steam password or Steam Guard code.
   To only generate the VDF without uploading, manually run `powershell ./tools/package/publish_steam.ps1 -Preview`.

Notes:

1. If any step fails (non-zero exit code), stop immediately and report the error to the user.
2. Never echo the Steam password, Steam Guard token, `CWS_DEFAULT_LLM_API_KEY`, or any raw key in the conversation.
3. After the upload completes, report the git tag, content root, and build version to the user, and remind them that if setlive was not set, they need to push the build to the target branch in the Steamworks dashboard.
