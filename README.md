# tg-router

Route messages to named Telegram chats through one bot and a small web API.
Registrations and short-lived registration links are stored in SQLite.

## Configuration

Set the bot token from BotFather and a separate API key for registration requests:

```bash
export TG_ROUTER_BOT_TOKEN=<TOKEN>
export TG_ROUTER_API_KEY=<RANDOM_SECRET>
```

Optional settings:

```bash
# Default: ./registrations.db
export TG_ROUTER_DATABASE=/path/to/registrations.db

# Registration-link lifetime in seconds; default: 600
export TG_ROUTER_REGISTRATION_TTL_SECONDS=600
```

Run the service:

```bash
uv run uvicorn server:app --app-dir src --port 8000
```

The service validates the bot token and starts Telegram polling at startup. Run
only one polling instance for a bot token.

## Docker

The Docker Compose configuration deploys the image published to GitHub
Container Registry: `ghcr.io/chusiksmirnov/tg-router:latest`.

```bash
cp .env.example .env  # then set TG_ROUTER_BOT_TOKEN and TG_ROUTER_API_KEY
docker compose pull
docker compose up -d
```

Run `docker compose pull && docker compose up -d` to update an existing
deployment to the latest published image. The API is served on `localhost:8000`.
The SQLite database is stored in the `registrations` volume at
`/data/registrations.db`.

## Web UI

Open `http://localhost:8000/` to manage routes in the browser. The Pico.css UI
lists registered chats, creates the time-limited Telegram links, and sends messages.
The registration API key is submitted only to create a registration link and is not
stored by the UI.

## API

### Register a chat

Creating or replacing a registration requires the `X-API-Key` header. This
prevents callers from taking over an existing routing name.

A `POST` request to the bot name creates a one-time registration link:

```bash
curl -X POST localhost:8000/bots/alerts \
  -H "X-API-Key: $TG_ROUTER_API_KEY"
```

Example response:

```json
{
  "name": "alerts",
  "expires_at": "2026-08-23T12:10:00Z",
  "private_chat_url": "https://t.me/example_bot?start=...",
  "group_chat_url": "https://t.me/example_bot?startgroup=..."
}
```

Open the appropriate link in Telegram. Once the bot receives the `/start`
command, the link is consumed and the chat is stored as `alerts`. Links expire
after `TG_ROUTER_REGISTRATION_TTL_SECONDS`; creating another link for the same
name immediately invalidates the previous one. Registration names may contain
only letters, digits, `_`, and `-`.

### Send a message

```bash
curl -X POST localhost:8000/bots/alerts/messages \
  -H 'content-type: application/json' \
  -d '{"text": "hello"}'
```

Example response:

```json
{"ok": true}
```

Format with HTML or MarkdownV2 by setting `parse_mode`:

```bash
curl -X POST localhost:8000/bots/alerts/messages \
  -H 'content-type: application/json' \
  -d '{"text": "<b>bold</b> code: <code>1+1=2</code> 🚀", "parse_mode": "HTML"}'
```

### List registered chats

```bash
curl localhost:8000/bots
```

Example response:

```json
[
  {
    "name": "alerts",
    "chat_id": -456,
    "chat_type": "group",
    "title": "Alerts",
    "username": "alerts-ops",
    "first_name": "Alert",
    "last_name": "Ops",
    "language_code": "en"
  }
]
```

### Health check

```bash
curl localhost:8000/health
```

Example response:

```json
{"ok": true}
```

## Running tests

Run the pytest suite (in `src/test_*.py`):

```bash
uv run pytest src/
```
