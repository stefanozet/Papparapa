# Deploy su server Hetzner (senza DNS)

Procedura per esporre Papparapa su internet da un server Hetzner (Ubuntu),
usando `sslip.io` per ottenere un hostname pubblico HTTPS senza possedere un
dominio.

Da eseguire su una sessione **root** del server (console Hetzner o SSH).

## Parametri di questo server

| Parametro | Valore |
|---|---|
| IP pubblico | `167.233.230.86` |
| Hostname (sslip.io) | `167-233-230-86.sslip.io` |
| Utente applicativo | `bor` |
| Path progetto | `/home/bor/git/Papparapa` |
| Venv backend | `/home/bor/git/Papparapa/backend/.venv` (già creato) |
| Porta interna app | `127.0.0.1:8000` |

`sslip.io` risolve automaticamente `167-233-230-86.sslip.io` all'IP
`167.233.230.86`: nessuna registrazione o configurazione DNS necessaria, e
Let's Encrypt può emettere un certificato valido su quell'hostname perché è
pubblicamente risolvibile.

## 1. Servizio systemd per l'app

Espone l'app solo su `127.0.0.1:8000` (non direttamente su internet); ci
pensa Apache a fare da reverse proxy pubblico.

```bash
cat > /etc/systemd/system/papparapa.service << 'EOF'
[Unit]
Description=Papparapa FastAPI app
After=network.target

[Service]
Type=simple
User=bor
Group=bor
WorkingDirectory=/home/bor/git/Papparapa/backend
Environment=PAPPARAPA_SECRET_KEY=7f3d9aa2ed5df1ea7dfbdee580acff1ce72aa799e12e4493ed9afc932baf7174
ExecStart=/home/bor/git/Papparapa/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now papparapa
systemctl status papparapa --no-pager
```

`--workers 1` è intenzionale: il DB è SQLite (file singolo), più worker
concorrenti in scrittura possono dare errori "database is locked".

Verifica locale:

```bash
curl -I http://127.0.0.1:8000
```

Deve rispondere `200 OK`.


### 2.1 Abilitare ProxyPreserveHost su Ubuntu

ProxyPreserveHost, ProxyPass, ProxyPassReverse ecc. sono fornite da mod_proxy e mod_proxy_http, che su Ubuntu non sono attivi di default.

Sul server esegui:
```bash
a2enmod proxy proxy_http
apache2ctl configtest    # deve rispondere "Syntax OK"
systemctl restart apache2
```

## 2. Apache come reverse proxy (porta 80 → 8000)

```bash
a2enmod proxy proxy_http ssl headers

cat > /etc/apache2/sites-available/papparapa.conf << 'EOF'
<VirtualHost *:80>
    ServerName 167-233-230-86.sslip.io

    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

    ErrorLog ${APACHE_LOG_DIR}/papparapa_error.log
    CustomLog ${APACHE_LOG_DIR}/papparapa_access.log combined
</VirtualHost>
EOF

a2dissite 000-default
a2ensite papparapa
systemctl reload apache2
```

Test (ancora senza HTTPS):

```bash
curl -I http://167-233-230-86.sslip.io
```

## 3. Certificato HTTPS gratuito (Let's Encrypt via certbot)

```bash
apt update
apt install -y certbot python3-certbot-apache

certbot --apache -d 167-233-230-86.sslip.io \
  --non-interactive --agree-tos -m stefano.rubini@gmail.com --redirect
```

`--redirect` configura il redirect automatico HTTP→HTTPS. Certbot installa
anche un timer systemd per il rinnovo automatico (verificabile con
`systemctl list-timers | grep certbot`).

## 4. Firewall locale (ufw)

```bash
ufw allow OpenSSH
ufw allow 'WWW Full'
ufw enable
ufw status verbose
```

## 5. Firewall Hetzner Cloud (lato pannello, obbligatorio)

Nel [Hetzner Cloud Console](https://console.hetzner.cloud) → progetto →
server → scheda **Firewalls**: assicurarsi che esista una regola inbound che
permetta **TCP 80** e **TCP 443** da `0.0.0.0/0` (oltre alla 22 per SSH).
Senza questo passaggio il server non è raggiungibile dall'esterno anche se
Apache e ufw sono configurati correttamente.

## 6. Verifica finale

Da un client esterno (non dal server stesso):

```bash
curl -I https://167-233-230-86.sslip.io
```

Deve rispondere `200 OK` con certificato valido. Poi aprire
`https://167-233-230-86.sslip.io` da browser/smartphone per testare l'app.

## Note

- La `PAPPARAPA_SECRET_KEY` nel file di systemd deve restare segreta: il file
  unit è leggibile solo da root (`/etc/systemd/system/papparapa.service`,
  permessi di default `644` ma contenuto letto solo da systemd/root in fase
  di avvio — se il server viene condiviso con altri utenti valutare
  `chmod 600`).
- Il database SQLite vive in `backend/papparapa.db`: è un file singolo, va
  incluso in eventuali backup.
- Per aggiornare il codice: `git pull` nella cartella del progetto, poi
  `systemctl restart papparapa`.
</content>
