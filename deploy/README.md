# Deploy (single Linux VM — DigitalOcean droplet)

One VM runs both APIs (bound to localhost) behind **Caddy**, which serves the UI and
proxies `/api` and `/translate`. Everything is one origin -> no CORS, no mixed content.

```
Internet --80/443--> Caddy --> /            static UI (tools/lyrics_operator/ui)
                               /api/*       127.0.0.1:8000 (lyrics-search)
                               /translate/* 127.0.0.1:8100 (lyrics-translate)
```

The EasyWorship **import server stays on each Windows PC** (127.0.0.1:3000); it is never deployed here.

This guide uses droplet IP **159.65.231.252**, clone path **/opt/projection**, and the default droplet user **root**.

---

## 1. Networking / IP (DigitalOcean)

- A droplet's public IP is **already static** — it stays with the droplet. No "reserved IP"
  needed unless you later want failover (DO's *Reserved IPs*).
- Firewall — only act if you turned these on:
  - **DO Cloud Firewall** (Networking → Firewalls): add inbound TCP **22, 80, 443**.
  - **ufw** on the droplet (off by default on DO images). If active:
    ```bash
    sudo ufw allow 22,80,443/tcp && sudo ufw status
    ```
- **HTTPS needs a hostname** (Let's Encrypt won't issue certs for a bare IP). Pick one:
  - **HTTP now (simplest):** keep Caddy site as `:80`, browse `http://159.65.231.252/`.
  - **Free HTTPS, no DNS:** `nip.io` — use `159.65.231.252.nip.io` as the Caddy site.
  - **Free HTTPS:** DuckDNS (`yourname.duckdns.org` → 159.65.231.252).
  - **Your domain:** `A` record → 159.65.231.252.

## 2. Install (as root)

```bash
apt update
apt install -y git python3-venv caddy
git clone <your-repo-url> /opt/projection
cd /opt/projection

# lyrics-search
cd services/lyrics-search
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp .env.example .env   # set GEMINI_API_KEY (and GENIUS_ACCESS_TOKEN if used)

# lyrics-translate
cd ../lyrics-translate
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp .env.example .env   # set GEMINI_API_KEY (same key is fine)
```

## 3. Run the APIs as services

```bash
cd /opt/projection
cp deploy/systemd/lyrics-search.service /etc/systemd/system/
cp deploy/systemd/lyrics-translate.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now lyrics-search lyrics-translate
systemctl status lyrics-search lyrics-translate --no-pager
```

Quick local check (before Caddy):

```bash
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8100/healthz
```

## 4. Caddy (UI + proxy)

```bash
cp deploy/Caddyfile /etc/caddy/Caddyfile
# Default is :80 (HTTP on the bare IP). To enable free HTTPS, change the first
# line of the block from  :80  to  159.65.231.252.nip.io
nano /etc/caddy/Caddyfile
systemctl reload caddy
```

The Caddy `caddy` user must be able to read the UI files — `/opt/projection` is fine
(world-readable). Don't put the repo under `/root` (mode 700; Caddy can't read it).

## 5. Verify

```bash
# HTTP (default :80)
curl http://159.65.231.252/api/healthz
curl http://159.65.231.252/translate/healthz
```

Open `http://159.65.231.252/` — the UI's API/Translate fields show `auto` and resolve to
same-origin `/api` and `/translate` (no per-PC config needed).

## 6. Church PCs (desktop import)

On each Windows PC, point the desktop window at the cloud UI; import stays local:

```powershell
$env:LYRICS_OPERATOR_UI_URL = "http://159.65.231.252/"   # or your https host
& "...\tools\lyrics_operator\desktop\run-desktop.ps1"
```

## Updating

```bash
cd /opt/projection && git pull
systemctl restart lyrics-search lyrics-translate   # if backend code changed
# UI changes are served immediately by Caddy (static files)
```

## Notes

- The UI auto-selects same-origin `/api` and `/translate` when not on localhost, so there
  is nothing to configure per environment. The header fields can still override if needed.
- `serve_ui.py` is dev-only; in the cloud Caddy serves the UI.
- With **HTTP** UI, the desktop import (`http://127.0.0.1:3000`) is same-scheme and works.
  If you switch the UI to **HTTPS**, localhost import still works in Chromium/WebView2
  (localhost is a trusted exception); Safari is stricter.
```
