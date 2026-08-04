# tg-router

Store Telegram bots and route messages to their chats via a web API. Each
registration binds one bot to one chat under a name; a web request that names
the bot resolves both the token and the chat_id from a flat XML file.

Register a bot and chat (prints a one-time deep link to open in Telegram):

```
uv run ./src/main.py --register alerts --token <TOKEN>
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

## Running tests

Run the pytest suite (in `src/test_*.py`):

```
uv run pytest src/
```
