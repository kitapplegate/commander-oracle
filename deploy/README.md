# Deploying the price pipeline

This is how the pipeline runs on a Linux server with systemd, under its own
unprivileged user. Run these steps as root.

```sh
useradd --system --create-home --home-dir /opt/commander-oracle --shell /usr/sbin/nologin oracle
sudo -u oracle git clone https://github.com/kitapplegate/commander-oracle /opt/commander-oracle/app
cd /opt/commander-oracle/app
sudo -u oracle python3 -m venv .venv
sudo -u oracle .venv/bin/pip install -q -r requirements.txt

# first run: card list + today's prices, then ~90 days of history
sudo -u oracle .venv/bin/python -m oracle.daily --refresh
sudo -u oracle .venv/bin/python -m oracle.daily --backfill

cp deploy/*.service deploy/*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now commander-oracle-daily.timer commander-oracle-backfill.timer
```

## Checking on it

```sh
systemctl list-timers 'commander-oracle-*'
journalctl -u commander-oracle-daily -n 20
sudo -u oracle sqlite3 /opt/commander-oracle/app/data/universe.sqlite \
  "SELECT started, price_day, status, cards_priced, note FROM runs ORDER BY started DESC LIMIT 7"
```

Every run writes a row to `runs`: `ok`, `stale` (MTGJSON hadn't published a new
day yet), `backfill`, or `failed` with the error in `note`. A failed run also
shows as a failed unit in `systemctl`.

## Updating

```sh
cd /opt/commander-oracle/app && sudo -u oracle git pull -q && sudo -u oracle .venv/bin/pip install -q -r requirements.txt
```
