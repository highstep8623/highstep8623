# Deployment Guide

This document explains how to package and deploy the RenovaHub marketplace on a typical Linux-based cloud host (e.g. Heroku, Render, AWS EC2, DigitalOcean).

## 1. Prerequisites

- Python 3.11 or newer.
- Git for source control.
- A process supervisor (systemd, supervisor, or `forever`/`pm2` if containerising).
- Optional: Nginx or Apache to reverse-proxy TLS traffic to the Python server.

## 2. Environment Configuration

1. Clone the repository and change into the project directory.
2. Create a Python virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. Install system packages (none required beyond the Python standard library).
4. Set environment variables:
   - `MARKETPLACE_SECRET`: random 32+ character string for JWT signing.
   - `PORT`: (optional) port that the HTTP server should bind to.

## 3. Database

The application uses SQLite by default (`marketplace/marketplace.db`). For production deployments you may want to use PostgreSQL or MySQL. To do so:

1. Provision the target database.
2. Replace the connection logic in `marketplace/database.py` with an appropriate driver (e.g., `psycopg` or `mysqlclient`).
3. Ensure all schema creation statements run on the new database (e.g., via migrations or manual SQL execution).

For lightweight deployments the bundled SQLite database is sufficient. Use the tests and sample data to seed initial content.

## 4. Static Assets

The frontend assets are stored in `frontend/`. When deploying behind a reverse proxy, configure the proxy to serve these files directly for optimal performance. Example Nginx snippet:

```
location /static/ {
    alias /var/www/renovahub/frontend/;
}
```

Alternatively, leave the Python server to serve the files (default behaviour).

## 5. Running the Application

Start the HTTP server with:

```bash
export MARKETPLACE_SECRET="change-me"
python -m marketplace.server
```

Use a process manager (e.g., systemd) to keep the service running:

```
[Unit]
Description=RenovaHub Marketplace
After=network.target

[Service]
User=www-data
WorkingDirectory=/srv/renovahub
Environment="MARKETPLACE_SECRET=change-me"
ExecStart=/srv/renovahub/venv/bin/python -m marketplace.server
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable renova
sudo systemctl start renova
```

## 6. TLS & Domains

Terminate TLS at a reverse proxy (Nginx/Apache) or use a managed certificate service. Forward traffic to the Python server running on localhost (port 8000 by default).

## 7. Monitoring & Logs

- Logs are written to stdout/stderr by default; configure your process manager to capture them.
- Use health-check endpoints by issuing `GET /api/homeowner/projects` or `/api/contractor/projects` with authentication tokens.
- Implement additional alerting by tailing logs for `error` responses or database exceptions.

## 8. Backups

Regularly back up the SQLite database (or RDBMS snapshots). For SQLite:

```bash
sqlite3 marketplace/marketplace.db ".backup '/backups/renovahub-$(date +%F).db'"
```

Automate this using cron or a managed backup service.

## 9. Scaling

- Horizontal scaling requires a shared database and possibly sticky sessions if you add server-side sessions in the future.
- Serve static files via CDN to reduce load.
- Consider containerisation (Docker) for reproducible builds.

## 10. Smoke Testing After Deploy

1. Hit the home page to verify static assets load.
2. Register a homeowner and contractor account.
3. Post a project and submit a quote.
4. Accept the quote and confirm that an invoice record appears (`GET /api/contractor/dashboard`).
5. Review logs to ensure no unhandled exceptions occurred.

Following these steps ensures a reliable and maintainable deployment of the RenovaHub marketplace.
