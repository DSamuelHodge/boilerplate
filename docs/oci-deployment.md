# OCI Deployment — restack boilerplate (us-chicago-1)

Live deployment of this boilerplate on Oracle Cloud Infrastructure,
fronted by Cloudflare Tunnel (no public ingress ports).

## Compute

- Shape: `VM.Standard.A1.Flex` (Ampere ARM, `aarch64`), 4 OCPU / 24 GB RAM
- Boot volume: 200 GB (Docker data-root lives on the boot volume)
- Image: Canonical Ubuntu 24.04 aarch64
- Hostname: `restack-vm`, user `ubuntu`
- Swap: 4 GB at `/swapfile` (8 GB was used for the first image build, then reduced)
- SSH: key `~/.ssh/restack_vm` (private key and pub in `pass`: `ssh/restack_vm`)
- OCI security list: no public ingress (port 22 closed); Cloudflared needs
  only stateful egress TCP 443 (plus UDP 7844 for QUIC)

## Cloudflare Tunnel

- Tunnel name: `restack-vm`
- Token in `pass`: `cloudflare/tunnel-restack`
- Ingress:
  - `ssh-restack.hodgeluke.com` → `ssh://localhost:22`
  - `restack.hodgeluke.com` → `http://localhost:3000` (Next.js frontend)
  - `mcp-restack.hodgeluke.com` → `http://localhost:11233` (`/mcp` endpoint)
  - `slack-restack.hodgeluke.com` → `http://localhost:3002` (slack-bot HTTP receiver: OAuth callback + events)
- SSH over tunnel: `cloudflared access tcp --hostname
  ssh-restack.hodgeluke.com --url 127.0.0.1:2229`, then
  `ssh -i ~/.ssh/restack_vm -p 2229 ubuntu@127.0.0.1`

## App environment (set before `prod:up`)
> `.env.example` targets local dev (app on host, infra in Docker) and
> uses `localhost` for database hosts. Under `prod:up` the backend also
> runs in Docker, so point the URLs at compose service names or the
> backend waits on PostgreSQL forever and every workflow (including
> sign-in) times out after 30s:
> `DATABASE_URL=...@postgres:5432/...`,
> `CLICKHOUSE_URL=...@clickhouse:8123/...`,
> `COCKROACHDB_URL=...@cockroachdb:26257/...`.

- `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` — generated with
  `openssl rand -base64 32`, stored in `pass` at
  `restack/NEXT_SERVER_ACTIONS_ENCRYPTION_KEY`. Must be in `.env`
  before the frontend image build (runtime-only injection breaks server actions).
- `RESTACK_ENGINE_MCP_ADDRESS=https://mcp-restack.hodgeluke.com`
  — OpenAI tool calls cannot use localhost.
- `SLACK_HTTP_BASE_URL=https://slack-restack.hodgeluke.com` — the
  Slack OAuth `redirect_uri` (`…/slack/oauth/callback`) is built from
  this. The old default (`http://localhost:3002`) made Slack bounce
  the browser to localhost, so "Add to Slack" never completed.
  `FRONTEND_URL=https://restack.hodgeluke.com` is the post-OAuth
  return target. Both are also the baked-in defaults in
  `apps/slack-bot/src/config.py` and `docker-compose.yml` (slack-bot).
  After starting the bot, register
  `https://slack-restack.hodgeluke.com/slack/oauth/callback` under
  the Slack app's OAuth & Permissions → Redirect URLs.

## ARM build note

`apps/backend/Dockerfile` carries `build-essential`, `pkg-config`,
and `libssl-dev` so `embed-anything` (Rust extension via `openssl-sys`)
compiles on `aarch64`. Upstream images this replaces:
`ghcr.io/restackio/restack:main` is multi-arch (`amd64`+`arm64`),
as are Postgres 17, ClickHouse, and CockroachDB.

## Deploy / verify

```bash
pnpm install
docker compose up -d --build   # pnpm prod:up
curl -sI http://localhost:3000 # 200 on the VM
curl -s -o /dev/null -w "%{http_code}" https://restack.hodgeluke.com # 200
```

MCP check: POST a JSON-RPC `initialize` to
`https://mcp-restack.hodgeluke.com/mcp` and expect a `restack-mcp`
handshake in reply.
