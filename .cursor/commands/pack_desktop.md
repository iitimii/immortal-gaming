When the user invokes this command, strictly follow the desktop Electron packaging flow.

This is the current default desktop build entry point. It only produces a releasable Windows Electron unpacked directory and does not upload to any store.

1. **Build and package**:
   Run `powershell ./tools/package/pack_desktop.ps1` and wait for it to finish.
   The script builds the web frontend, the PyInstaller backend, and the Electron shell, and writes the final content root to `tmp/desktop_content_root.txt`.

Notes:

1. If any step fails (non-zero exit code), stop immediately and report the error to the user.
2. Never echo `CWS_DEFAULT_LLM_API_KEY` or any raw key in the conversation.
3. When packaging finishes, report the git tag, content root, and build desc to the user.
