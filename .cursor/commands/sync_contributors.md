When the user invokes this command, sync and update the repository root `CONTRIBUTORS.md` and the contributors section of `README.md`, using the GitHub repository contributor list as the source. The whole flow is driven by `tools/github/sync_contributors.py`.

Strictly follow this flow:

1. **Confirm the target repository**:
   - The default repository is `4thfever/cultivation-world-simulator`
   - Only override it when the user explicitly specifies another repository
2. **Run the sync script**:
   - Run `python tools/github/sync_contributors.py`
   - To specify a repository, use `python tools/github/sync_contributors.py --repo owner/name`
3. **Generated document requirements**:
   - The output target is the repository root `CONTRIBUTORS.md`
   - Keep the note thanking open-source contributors at the top of the document
   - Render the contributor list as a Markdown table
   - The table keeps only three columns: `Name`, `Avatar`, `GitHub`
   - Do not add descriptions of "what each person did"
   - The table data must follow the GitHub contributors API response
4. **Sync `README.md`**:
   - The script automatically updates the contributors section of `README.md` (the section heading it matches is defined in `tools/github/sync_contributors.py`)
   - The contributor avatars in `README.md` must map one-to-one to the GitHub contributors API result (same count and identities)
   - Do not rely solely on third-party aggregate images (such as contrib.rocks) as the only display source, to avoid missing avatars caused by caching/filtering
   - If an avatar wall or grid is used, render it directly from the list returned by the API, and keep links pointing to the correct GitHub profiles
5. **Failure handling**:
   - If the GitHub API request fails, state the failure reason clearly
   - Never write fabricated or hand-filled contributor data when the request fails
6. **Self-check when done**:
   - Check that `CONTRIBUTORS.md` was updated
   - Check that the contributors section of `README.md` was synced
   - Check that the table is readable and links point to the correct GitHub profiles
   - Output the total number of contributors synced this run

Notes:

- Only update `CONTRIBUTORS.md`, `README.md`, and the necessary script; do not touch other business files along the way.
- If you added or modified `.cursor/commands`, consider running `/sync_agents` afterwards to keep the `AGENTS.md` index in sync.
