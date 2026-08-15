# tg-router

Store Telegram chats and route messages to them via a web API using a single bot
token from the environment. Each registration binds one chat to a name in a flat
XML file; a web request that names the chat resolves the `chat_id`, and messages
are sent with the shared token.

Set the bot token from BotFather once:

```
export TG_ROUTER_TOKEN=<TOKEN>
```

Optionally override where registrations are stored (default
`./registrations.xml`):

```
export TG_ROUTER_REGISTRATIONS=/path/to/registrations.xml
```

Register a chat (prints a one-time deep link to open in Telegram). The name
may only contain letters, digits, `_` and `-`; it is the key used in the API
paths. Use `-r/--registrations` to store registrations in another file:

```
uv run ./src/main.py --register alerts
```

Serve the web API:

```
uv run uvicorn server:app --app-dir src --port 8000
```

Send a message to the registered chat (plain text by default):

```
curl -X POST localhost:8000/bots/alerts/messages \
  -H 'content-type: application/json' -d '{"text": "hello"}'
```

Format with HTML or MarkdownV2 by setting `parse_mode`:

```
curl -X POST localhost:8000/bots/alerts/messages \
  -H 'content-type: application/json' \
  -d '{"text": "<b>bold</b> code: <code>1+1=2</code> 🚀", "parse_mode": "HTML"}'
```

List registered chats:

```
curl localhost:8000/bots
```

## Running tests

Run the pytest suite (in `src/test_*.py`):

```
uv run pytest src/
```
