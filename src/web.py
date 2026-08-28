from fastapi.responses import HTMLResponse

WEB_UI = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>tg-router</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
  </head>
  <body>
    <main class="container">
      <nav><ul><li><strong>tg-router</strong></li></ul><ul><li><a href="#chats">Registered chats</a></li></ul></nav>
      <header>
        <hgroup><h1>Telegram router</h1><p>Create named chat routes and send messages without using the REST API manually.</p></hgroup>
      </header>

      <article>
        <header><strong>Create registration</strong></header>
        <form id="registration-form">
          <label>Route name <input id="registration-name" name="name" required pattern="[A-Za-z0-9_-]+" placeholder="alerts"></label>
          <label>API key <input id="api-key" name="api-key" type="password" autocomplete="off" required></label>
          <button type="submit">Create Telegram links</button>
        </form>
        <div id="registration-result" hidden></div>
      </article>

      <article>
        <header><strong>Send message</strong></header>
        <form id="message-form">
          <label>Route <select id="message-route" name="route" required><option value="">Choose a registered chat…</option></select></label>
          <label>Message <textarea id="message-text" name="text" required maxlength="4096" placeholder="Write a message…"></textarea></label>
          <label>Formatting <select id="parse-mode" name="parse-mode"><option value="">Plain text</option><option value="HTML">HTML</option><option value="Markdown">Markdown</option><option value="MarkdownV2">MarkdownV2</option></select></label>
          <button type="submit">Send message</button>
        </form>
        <p id="message-result" aria-live="polite"></p>
      </article>

      <article id="chats">
        <header><strong>Registered chats</strong></header>
        <figure><table><thead><tr><th>Route</th><th>Chat</th><th>Type</th></tr></thead><tbody id="chat-list"><tr><td colspan="3" aria-busy="true">Loading…</td></tr></tbody></table></figure>
        <footer><button id="refresh-chats" class="secondary">Refresh</button></footer>
      </article>
    </main>
    <script>
      const $ = (selector) => document.querySelector(selector);
      const errorText = async (response) => {
        const body = await response.json().catch(() => ({}));
        return body.detail || `Request failed (${response.status})`;
      };
      const showRegistration = (registration) => {
        const result = $('#registration-result'); result.hidden = false; result.replaceChildren();
        const instruction = document.createElement('p');
        instruction.textContent = `Open one link before ${new Date(registration.expires_at).toLocaleString()}:`;
        const links = document.createElement('p');
        for (const [label, url] of [['Open private chat', registration.private_chat_url], ['Add to group', registration.group_chat_url]]) {
          const link = document.createElement('a'); link.href = url; link.target = '_blank'; link.rel = 'noopener'; link.textContent = label;
          links.append(link, document.createElement('br'));
        }
        result.append(instruction, links);
      };
      const showRegistrationError = (message) => {
        const result = $('#registration-result'); result.hidden = false; result.replaceChildren();
        const error = document.createElement('mark'); error.textContent = message; result.append(error);
      };
      async function loadChats() {
        const list = $('#chat-list');
        try {
          const response = await fetch('/bots');
          if (!response.ok) throw new Error(await errorText(response));
          const chats = await response.json();
          $('#message-route').innerHTML = '<option value="">Choose a registered chat…</option>';
          list.replaceChildren();
          if (!chats.length) { list.innerHTML = '<tr><td colspan="3">No chats registered yet.</td></tr>'; return; }
          for (const chat of chats) {
            const option = new Option(chat.name, chat.name); $('#message-route').add(option);
            const row = document.createElement('tr');
            for (const value of [chat.name, chat.title || chat.username || chat.first_name || String(chat.chat_id), chat.chat_type]) {
              const cell = document.createElement('td'); cell.textContent = value; row.append(cell);
            }
            list.append(row);
          }
        } catch (error) { list.innerHTML = ''; const row = list.insertRow(); const cell = row.insertCell(); cell.colSpan = 3; cell.textContent = `Could not load chats: ${error.message}`; }
      }
      $('#registration-form').addEventListener('submit', async (event) => {
        event.preventDefault();
        const name = $('#registration-name').value;
        const response = await fetch(`/bots/${encodeURIComponent(name)}`, { method: 'POST', headers: {'X-API-Key': $('#api-key').value} });
        if (!response.ok) { showRegistrationError(await errorText(response)); return; }
        const registration = await response.json();
        showRegistration(registration);
      });
      $('#message-form').addEventListener('submit', async (event) => {
        event.preventDefault();
        const parseMode = $('#parse-mode').value;
        const response = await fetch(`/bots/${encodeURIComponent($('#message-route').value)}/messages`, { method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify({text: $('#message-text').value, ...(parseMode && {parse_mode: parseMode})}) });
        $('#message-result').textContent = response.ok ? 'Message sent.' : await errorText(response);
        if (response.ok) $('#message-text').value = '';
      });
      $('#refresh-chats').addEventListener('click', loadChats); loadChats();
    </script>
  </body>
</html>"""


def web_ui() -> HTMLResponse:
    return HTMLResponse(WEB_UI)
