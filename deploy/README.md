# Deploy (single Linux VM, e.g. OCI free tier)

One VM runs both APIs (bound to localhost) behind **Caddy**, which serves the UI and
proxies `/api` and `/translate`. Everything is one origin -> no CORS, no mixed content.

```
Internet --443--> Caddy --> /            static UI (tools/lyrics_operator/ui)
                            /api/*       127.0.0.1:8000 (lyrics-search)
                            /translate/* 127.0.0.1:8100 (lyrics-translate)
```

The EasyWorship **import server stays on each Windows PC** (127.0.0.1:3000); it is never deployed here.

---

## 1. Networking / IP (OCI specifics)

1. **Reserve a public IP** and attach it to the instance VNIC (free-tier ephemeral IPs can change on stop/start). Point your DNS `A` record at it.
2. **Open ports in TWO places** (the #1 OCI gotcha):
   - **Security List / NSG** (console): ingress for TCP **22, 80, 443**.
   - **Host firewall** (on the VM):
     ```bash
     sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
     sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
     sudo netfilter-persistent save
     ```
3. **Hostname for HTTPS** — pick one:
   - real domain -> `A` record to the reserved IP, or
   - free **DuckDNS** (`yourname.duckdns.org`), or
   - HTTP only on the bare IP (set the Caddy site to `:80`, no TLS).

## 2. Install

```bash
sudo apt update
sudo apt install -y git python3-venv caddy
git clone <your-repo-url> /home/ubuntu/projection
cd /home/ubuntu/projection

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
cd /home/ubuntu/projection
sudo cp deploy/systemd/lyrics-search.service /etc/systemd/system/
sudo cp deploy/systemd/lyrics-translate.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now lyrics-search lyrics-translate
systemctl status lyrics-search lyrics-translate --no-pager
```

(Adjust `User=` and the `/home/ubuntu/projection` paths in the unit files if your VM differs.)

## 4. Caddy (UI + proxy + HTTPS)

```bash
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile
sudo nano /etc/caddy/Caddyfile      # set your hostname and UI path
sudo systemctl reload caddy
```

Caddy fetches/renews the TLS cert automatically once DNS points at the VM.

## 5. Verify

```bash
curl -k https://YOUR-HOST/api/healthz
curl -k https://YOUR-HOST/translate/healthz
```

Open `https://YOUR-HOST/` — the UI's API/Translate fields show `auto` and resolve to
same-origin `/api` and `/translate` (no per-PC config needed).

## 6. Church PCs (desktop import)

On each Windows PC, point the desktop window at the cloud UI; import stays local:

```powershell
$env:LYRICS_OPERATOR_UI_URL = "https://YOUR-HOST/"
& "...\tools\lyrics_operator\desktop\run-desktop.ps1"
```

## Updating

```bash
cd /home/ubuntu/projection && git pull
sudo systemctl restart lyrics-search lyrics-translate   # if backend code changed
# UI changes are served immediately by Caddy (static files)
```

## Notes

- The UI auto-selects same-origin `/api` and `/translate` when not on localhost, so there
  is nothing to configure per environment. The header fields can still override if needed.
- `serve_ui.py` is dev-only; in the cloud Caddy serves the UI.
- HTTPS UI -> `http://127.0.0.1:3000` import works in Chromium/WebView2 (localhost is a
  trusted exception). Test in the operators' browser; Safari is stricter.
