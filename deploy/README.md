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

## Buy/Hold/Sell accuracy replay (weekly)

`commander-oracle-replay.timer` runs `oracle.replay` every Monday at 09:00 UTC: it
replays the verdict logic as of 30 and 14 days ago and scores it against today's
prices. Read the latest result:

```sh
journalctl -u commander-oracle-replay -n 40 -o cat
```

## MTGJSON publish-time watch (temporary)

`commander-oracle-watch.timer` polls MTGJSON hourly and appends
`polled_utc  meta_date  prices_last_modified_utc` to `data/mtgjson-watch.tsv`.
It exists to find when MTGJSON actually publishes, so the daily timer can be
set after it. See what it has learned:

```sh
cd /opt/commander-oracle/app && sudo -u oracle .venv/bin/python -m oracle.watch --report
```

Once the daily timer is retimed, stop it: `systemctl disable --now commander-oracle-watch.timer`.

## Updating

```sh
cd /opt/commander-oracle/app && sudo -u oracle git pull -q && sudo -u oracle .venv/bin/pip install -q -r requirements.txt
```

# Deploying the website

The site is a static Vite build served by Caddy at oracle.marzipan-solutions.com,
from `/var/www/oracle.marzipan-solutions.com`:

- `index.html`, `assets/`, `favicon.svg`: owned by root, changed only by a deploy
- `data/cards.json`: in a folder owned by `oracle`; the daily unit rebuilds
  and publishes it (`oracle.build` -> `oracle.judge` -> `oracle.publish`).
  `oracle.publish` refuses empty or unjudged builds, so the site keeps its last
  good data.

Deploying frontend changes:

```sh
cd web && npm run build && cd dist && tar czf - . > ../../site.tgz && cd ../..
scp site.tgz root@<vps>:/tmp/oracle-site.tgz
# on the server: extract to a temp dir, copy assets/, favicon.svg and index.html into
# the web root as root; leave data/ alone (the pipeline owns it)
```

The Caddy block lives at the end of `/etc/caddy/Caddyfile` (backup:
`Caddyfile.bak-oracle-*`). That file serves every site on the box, so always run
`caddy validate --config /etc/caddy/Caddyfile` before `systemctl reload caddy`.

## The TypeSafe key on the server

`oracle.judge` needs `TYPESAFE_API_KEY` only when a card isn't in
`data/jev_cache.json` yet. It lives in `/opt/commander-oracle/app/.env`: mode
600, owner `oracle`, inside a 750 home directory that Caddy can't read. It is
never written to the web root, the logs, or git.
