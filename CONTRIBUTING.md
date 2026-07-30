# Contributing

Thank you for helping improve Bot News Telegram.

## Set up the project

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Use your own test configuration and never share tokens or API keys.

## Contribution guidelines

- Preserve the original source in story titles, previews, and links.
- Make sure new filters do not mix stories between topics.
- Explain why a scoring threshold needs to change.
- Do not remove deduplication without an equivalent replacement.
- Update the README when configuration or user-facing behavior changes.
- Never commit `.env` or runtime state files.

## Checks before committing

Check the Python syntax:

```powershell
python -m py_compile repurpose-bot.py
```

Run a single test cycle:

```powershell
$env:TEST_MODE="1"
python repurpose-bot.py
```

Review the logs for active topics, candidate counts, filter results, duplicate
detection, and delivery status.

## Commit messages

Use short and descriptive messages, for example:

- `docs: improve setup guide`
- `fix: prevent duplicate politics stories`
- `feat: add new RSS source`
