# Security policy

## Credentials

The bot uses a Telegram token and can optionally use a TwitterAPI.io API key.
Store real values in `.env` or your deployment platform's secret manager. Never
place them in source code, documentation, public issues, logs, or screenshots.

## If a secret is exposed

1. Rotate the token or API key with the relevant provider.
2. Update the secret on the deployment platform.
3. Remove the value from active files.
4. Remove it from the Git history; deleting the latest commit is not enough.
5. Review bot and API activity for anything unexpected.

## Runtime data

These files may reveal usage patterns and should remain private:

- `seen_items.json`;
- `sent_signatures.json`;
- `telegram_update_offset.json`.

All of them are included in `.gitignore`.

## Reporting a vulnerability

Do not open a public issue containing tokens, private chat IDs, group data, or
complete exploitation details. Contact the repository owner privately with a
short impact summary and sanitized reproduction steps.
