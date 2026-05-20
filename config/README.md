# Local Configuration

AresForge reads local operator settings from environment variables.

Start by copying `.env.example` to `.env`, then adjust values for your machine.

Important boundaries:

- Do not store real secrets in tracked files.
- The CLI reads GitHub owner and repo values as configuration only.
- The CLI does not perform autonomous GitHub state changes.
