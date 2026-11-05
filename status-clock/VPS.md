# Hostinger VPS deployment

This project lives in `romaroni/apps` under `status-clock/`. It can share a VPS
with other apps. Inspect existing containers, proxy configuration and ports before
deploying; do not replace another site's proxy or bind an occupied port.

## Prerequisites

- Docker Engine and the Docker Compose plugin installed on the VPS.
- A chosen display hostname pointing to the VPS.
- An existing or newly configured HTTPS reverse proxy, compatible with TLS 1.2
  for iOS 12. Do not expose the Python port directly on the public network.
- Read-only Notion integration shared only with Status, its token and page ID.

## Install

From a chosen applications directory on the VPS:

```sh
git clone https://github.com/romaroni/apps.git
cd apps/status-clock
umask 077
cp .env.example .env
nano .env
```

Fill in the four required variables from the README. Enter secrets in the VPS
editor, never in chat, Git commits or command arguments. `.env` must remain mode
600. If the repository is already cloned, use that checkout rather than cloning
over it. Port 8088 on loopback must be free; change the left side of the mapping
if needed.

```sh
docker compose up -d --build
docker compose ps
```

To test access protection, use:

```sh
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8088/clock
```

Expected: 401. Add a virtual host in the VPS's existing HTTPS proxy forwarding
the chosen hostname to `127.0.0.1:8088`. For a containerized proxy, loopback refers
to that proxy container; use a shared Docker network instead and remove the host
port mapping. Do not replace existing configuration. Redirect public HTTP to
HTTPS and verify the certificate chain on the actual iPad.

Open `https://YOUR-HOSTNAME/clock`, sign in, then check `/status`. Both routes and
the root must reject unauthenticated requests. Follow the README acceptance
checklist before handing over to Juliana.

## Update and recover

After reviewing and pulling an approved commit, run `docker compose up -d --build`
from this directory. Keep the previous working Git commit ID. Roll back by
checking out that commit and rebuilding; `.env` stays outside Git. Container
restart policy restores the service after a VPS reboot when Docker starts.
Back up `.env` in a secure secret store. No application data volume is required.

Live VPS inventory, hostname, proxy setup and credentials have not yet been
verified by this project. These instructions do not indicate a completed deploy.
