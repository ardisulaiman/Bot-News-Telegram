# Bot News Telegram

A multi-topic news curation bot for Telegram. It collects stories from RSS
feeds and X, evaluates relevance and virality, filters similar stories, and
sends the strongest results to the appropriate Telegram Topics.

The bot does not use generative AI. Titles and previews remain sourced from the
original publishers, making each story easy to review, verify, and rewrite
manually before publishing it elsewhere.

## Key features

- Curates AI tools & tutorials (setiap item dikasih ide konten: angle, ide
  judul, bahan bahasan — tema harian dirotasi biar idenya gak abis), crypto,
  Indonesian viral news, Indonesian entertainment, global viral news, and
  Indonesian politics (sumber diperluas: ANTARA, CNN ID, Tempo, Kompas via
  Google News, Detik, CNBC ID, Republika, Suara, dst).
- Skor minimal politik dinaikkan biar yang dikirim cuma yang paling viral.
- Uses a dedicated set of RSS feeds for each topic.
- Supports X as an optional source through TwitterAPI.io.
- Calculates viral scores from keywords, engagement, and cross-source coverage.
- Filters stories by topic relevance and publication age.
- Prevents duplicates using title tokens and important entities.
- Sends messages to Telegram Topics using `message_thread_id`.
- Provides a `/tr` command to translate replied messages into Indonesian.
- Includes a single-run test mode for safe validation.

## How it works

```text
RSS feeds + TwitterAPI.io
            ↓
    Time and topic filters
            ↓
       Viral scoring
            ↓
      Duplicate checks
            ↓
  Matching Telegram Topic
```

Each story receives a score based on:

1. X engagement or a base score for RSS sources;
2. major-update, controversy, and topic-specific keywords;
3. similar coverage from multiple publishers;
4. additional content filters for the selected category.

Previously sent stories are stored locally so they are not sent again during
future cycles.

## Requirements

- Python 3.11 or newer
- A Telegram bot created with `@BotFather`
- A Telegram group with Topics enabled
- A TwitterAPI.io API key if X sourcing is required

## Installation

Clone the repository:

```powershell
git clone https://github.com/ardisulaiman/Bot-News-Telegram.git
cd Bot-News-Telegram
```

Create a virtual environment and install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy the example configuration:

```powershell
Copy-Item .env.example .env
```

## Configuration

Open `.env` and provide the required values:

```dotenv
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

TOPIC_AI_THREAD_ID=
TOPIC_CRYPTO_THREAD_ID=
TOPIC_VIRAL_THREAD_ID=
TOPIC_ENTERTAINMENT_THREAD_ID=
TOPIC_VIRAL_GLOBAL_THREAD_ID=
TOPIC_POLITICS_THREAD_ID=

TWITTERAPI_KEY=
CHECK_INTERVAL_SECONDS=1800
MAX_AGE_HOURS=5
MAX_ITEMS_PER_TOPIC=6
POLITICS_MAX_ITEMS=15
DEDUPE_HOURS=72
TRANSLATE_SOURCE_LANG=en
TEST_MODE=0
```

### Find the Telegram chat ID

1. Add the bot to your Telegram group.
2. Make it an administrator so it can send messages to Topics.
3. Send a message to the group.
4. Open `https://api.telegram.org/bot<TOKEN>/getUpdates`.
5. Copy `message.chat.id` into `TELEGRAM_CHAT_ID`.

### Find a Topic thread ID

1. Enable Topics in the Telegram group.
2. Create a Topic for the category.
3. Send a message inside that Topic.
4. Open the `getUpdates` endpoint.
5. Copy `message_thread_id` into the matching environment variable.

Topics with an empty thread ID are skipped, so you only need to configure the
categories you want to use.

## Running the bot

Run one test cycle first:

```powershell
$env:TEST_MODE="1"
python repurpose-bot.py
```

When the output looks correct, start the regular loop:

```powershell
python repurpose-bot.py
```

The bot checks its sources, sends stories that pass curation, waits for
`CHECK_INTERVAL_SECONDS`, and repeats.

## Telegram command

Reply to an English message in the group and send:

```text
/tr
```

The bot translates the text or caption into Indonesian through MyMemory while
preserving URLs.

## Runtime files

The following files are created automatically and should not be committed:

- `seen_items.json`: IDs of processed stories;
- `sent_signatures.json`: title fingerprints used for deduplication;
- `telegram_update_offset.json`: the last Telegram update processed.

## Deployment

The repository includes the existing `railpack.toml` deployment configuration.
On your hosting platform, configure the same environment variables used in
`.env` and run `python repurpose-bot.py` as the main process. Never upload the
local `.env` file.

## Troubleshooting

### The bot does not send stories

Check the bot token, chat ID, thread IDs, story age limit, and minimum score for
each profile. The terminal logs identify skipped topics and rejected stories.

### Similar stories appear again

Make sure the runtime files remain writable and are not deleted after every
restart. Use persistent storage when deploying to an ephemeral hosting
environment.

### X returns no stories

Verify that `TWITTERAPI_KEY` is valid. RSS sources continue working when the key
is not configured.

### The `/tr` command does not respond

Make sure only one bot instance is consuming `getUpdates` and that the bot can
read messages in the group.

## Security

Never commit Telegram tokens, API keys, `.env`, or runtime data. If a secret is
ever exposed on GitHub, rotate it immediately and remove it from the Git
history.

## Maintenance note

RSS feeds, X data structures, and external APIs may change over time. Review the
logs regularly and replace sources that stop responding.
