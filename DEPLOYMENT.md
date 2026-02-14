# KidsClubPlans Conversational — Deployment Runbook

## Quick Reference

| Service | Command |
|---------|---------|
| Check backend status | `sudo systemctl status kcp-backend` |
| View logs | `sudo journalctl -u kcp-backend -f` |
| Restart backend | `sudo systemctl restart kcp-backend` |
| Test health | `curl https://chat.kidsclubplans.app/health` |

---

## Environment

**VPS:** 162.212.153.134 (Ubuntu)
**User:** openclaw
**Domain:** chat.kidsclubplans.app
**Backend Port:** 8000 (localhost)
**Nginx:** Reverse proxy + SSL

---

## Directory Structure

```
/home/openclaw/kidsclubplans-conversational/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app
│   │   ├── chat.py          # LLM streaming
│   │   ├── tools.py         # Tool definitions
│   │   ├── rag.py           # Vector search
│   │   └── memory.py        # SQLite persistence
│   ├── .env                 # API keys (not in git)
│   ├── requirements.txt
│   └── .venv/               # Python virtual env
├── frontend/                 # Built assets only on VPS
│   └── ...
└── .github/
    └── workflows/
        └── deploy.yml       # Auto-deploy action
```

---

## Deployment Flow

```
Developer push ──► GitHub ──► Actions ──► SSH to VPS ──► Pull ──► Restart
```

### Auto-Deploy Trigger
Any push to `main` branch triggers deployment:
1. GitHub Actions runs tests
2. SSH to VPS as `openclaw`
3. `git pull origin main`
4. `sudo systemctl restart kcp-backend`

---

## Manual Deployment (Emergency)

If auto-deploy fails:

```bash
# SSH to VPS
ssh openclaw@162.212.153.134

# Pull latest
cd /home/openclaw/kidsclubplans-conversational
git pull origin main

# Restart backend
sudo systemctl restart kcp-backend

# Verify
sudo systemctl status kcp-backend
curl https://chat.kidsclubplans.app/health
```

---

## Backend Service

### systemd Configuration
File: `/etc/systemd/system/kcp-backend.service`

```ini
[Unit]
Description=KidsClubPlans Conversational Backend
After=network.target

[Service]
Type=simple
User=openclaw
WorkingDirectory=/home/openclaw/kidsclubplans-conversational/backend
Environment=PATH=/home/openclaw/kidsclubplans-conversational/backend/.venv/bin
ExecStart=/home/openclaw/kidsclubplans-conversational/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Environment Variables (`.env`)
```bash
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=kcp-activities
OPENWEATHER_API_KEY=...  # Optional
```

---

## Nginx Configuration

File: `/etc/nginx/sites-available/chat.kidsclubplans.app.conf`

```nginx
server {
    server_name chat.kidsclubplans.app;
    
    # Chat endpoint (SSE) → backend
    location /chat {
        proxy_pass http://localhost:8000/chat;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_read_timeout 86400;
    }
    
    # API requests → Backend
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_buffering off;
    }
    
    # Static files (Next.js)
    location / {
        root /var/www/chat.kidsclubplans.app;
        try_files $uri $uri/ /index.html;
    }

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/chat.kidsclubplans.app/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/chat.kidsclubplans.app/privkey.pem;
}

# HTTP → HTTPS redirect
server {
    listen 80;
    server_name chat.kidsclubplans.app;
    return 301 https://$host$request_uri;
}
```

---

## Troubleshooting

### Backend Won't Start
```bash
# Check logs
sudo journalctl -u kcp-backend -n 50

# Verify Python env
source /home/openclaw/kidsclubplans-conversational/backend/.venv/bin/activate
python -c "import app.main"

# Check env vars
cat /home/openclaw/kidsclubplans-conversational/backend/.env
```

### Frontend 404 Errors
```bash
# Verify files exist
ls -la /var/www/chat.kidsclubplans.app/

# Check nginx error log
sudo tail -f /var/log/nginx/error.log
```

### Database Issues
```bash
# Check SQLite
sqlite3 /home/openclaw/kidsclubplans-conversational/backend/data/memory.db ".tables"

# Backup
cp /home/openclaw/kidsclubplans-conversational/backend/data/memory.db \
   /home/openclaw/backups/memory-$(date +%Y%m%d).db
```

### High Memory Usage
```bash
# Check process
ps aux | grep uvicorn

# Restart if needed
sudo systemctl restart kcp-backend
```

---

## Monitoring

### Key Metrics
| Metric | Check |
|--------|-------|
| Uptime | `curl -f https://chat.kidsclubplans.app/health` |
| Response Time | `time curl https://chat.kidsclubplans.app/health` |
| Error Rate | `sudo journalctl -u kcp-backend | grep ERROR | wc -l` |

### Log Rotation
```bash
# Install logrotate
sudo apt install logrotate

# Config at /etc/logrotate.d/kcp-backend
/home/openclaw/kidsclubplans-conversational/backend/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

---

## Security Checklist

- [ ] `.env` file has 600 permissions
- [ ] No API keys in git
- [ ] UFW firewall enabled
- [ ] Automatic security updates
- [ ] Fail2ban installed
- [ ] SSH key auth only (no password)

---

## Backup Strategy

### Daily (cron at 3am)
```bash
#!/bin/bash
BACKUP_DIR=/home/openclaw/backups
DATE=$(date +%Y%m%d)

# Database
sqlite3 /home/openclaw/kidsclubplans-conversational/backend/data/memory.db ".backup ${BACKUP_DIR}/memory-${DATE}.db"

# Configs
cp /home/openclaw/kidsclubplans-conversational/backend/.env ${BACKUP_DIR}/env-${DATE}

# Keep only 7 days
find ${BACKUP_DIR} -name "*.db" -mtime +7 -delete
find ${BACKUP_DIR} -name "env-*" -mtime +7 -delete
```

---

## GitHub Secrets

Required for auto-deploy:
- `VPS_HOST`: 162.212.153.134
- `VPS_USER`: openclaw
- `VPS_SSH_KEY`: Private SSH key (add public key to VPS authorized_keys)

---

*Last updated: 2026-02-14*
