When the user invokes this command, run the desktop Electron build and then enter the Epic BuildPatchTool upload flow.

Epic uploads go through `tools/package/epic/publish.ps1`, which calls the official `BuildPatchTool.exe -mode=UploadBinary`. By default no real upload happens; Epic services are only called when `-RequireUpload` is passed explicitly.

1. **Build, package, and enter the Epic upload preview**:
   Run `powershell ./tools/package/publish_epic.ps1 -RequireEosRuntime` and wait for it to finish.
   The script automatically runs `pack_desktop.ps1`, reads `tmp/desktop_content_root.txt`, then calls `epic/publish.ps1 -ContentRoot ... -BuildVersion <current git tag>-desktop`.
   Without `-RequireUpload`, the last step only validates the configuration and prints a redacted BuildPatchTool command.
   For a real upload, manually run `powershell ./tools/package/publish_epic.ps1 -RequireEosRuntime -RequireUpload`, and make sure `EPIC_CLIENT_SECRET` is set in the current terminal.

Notes:

1. If the desktop build fails, stop immediately and report the error to the user.
2. Never echo `CWS_DEFAULT_LLM_API_KEY`, the Epic client secret, or any raw key in the conversation.
3. Without `-RequireUpload`, skipping the Epic upload is expected behavior; still report the generated content root to the user.
4. Epic EOS uses the Live deployment by default. Add `-EosEnv dev` only for isolated Dev testing.
