# Fail2ban Configuration

Auto-bans malicious IPs scanning for vulnerabilities.

## How It Works

1. **nginx** writes access/error logs to `nginx_logs` volume
2. **fail2ban** reads those logs and matches against filter patterns
3. IPs matching patterns get banned via iptables on the host

## Jails Enabled

| Jail | What it catches | Ban time |
|------|-----------------|----------|
| `nginx-botsearch` | .env, .git, wp-admin, phpmyadmin scanners | 24 hours |
| `nginx-http-auth` | Failed auth attempts | 1 hour |
| `nginx-4xx` | Excessive 404/403 floods | 30 min |
| `nginx-limit-req` | Rate limit violations | 1 hour |

## Commands

```bash
# Check fail2ban status
docker exec fail2ban fail2ban-client status

# Check specific jail
docker exec fail2ban fail2ban-client status nginx-botsearch

# Manually ban an IP
docker exec fail2ban fail2ban-client set nginx-botsearch banip 1.2.3.4

# Manually unban an IP
docker exec fail2ban fail2ban-client set nginx-botsearch unbanip 1.2.3.4

# View banned IPs
docker exec fail2ban fail2ban-client get nginx-botsearch banned

# View fail2ban logs
docker logs fail2ban --tail 100
```

## Testing

```bash
# Test filter against log file (dry run)
docker exec fail2ban fail2ban-regex /var/log/nginx/access.log /etc/fail2ban/filter.d/nginx-botsearch.conf
```

## Files

```
fail2ban/
├── jail.d/
│   └── nginx.conf          # Jail definitions (what to watch, ban times)
├── filter.d/
│   ├── nginx-botsearch.conf # Pattern for vulnerability scanners
│   └── nginx-4xx.conf       # Pattern for 4xx floods
└── README.md
```

## Persistent Data

- `fail2ban_data` volume stores the ban database
- Bans survive container restarts
- Database auto-purges entries older than 14 days (F2B_DB_PURGE_AGE)

## Adding Your IP to Whitelist

Edit `jail.d/nginx.conf` and add to `[DEFAULT]`:

```ini
[DEFAULT]
ignoreip = 127.0.0.1/8 ::1 YOUR.IP.HERE
```

Then restart: `docker compose restart fail2ban`
