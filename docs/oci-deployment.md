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
- SSH over tunnel: `cloudflared access tcp --hostname
  ssh-restack.hodgeluke.com --url 127.0.0.1:2229`, then
  `ssh -i ~/.ssh/restack_vm -p 2229 ubuntu@127.0.0.1`

## App environment (set before `prod:up`)

- `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` — generated with
  `openssl rand -base64 32`, stored in `pass` at
  `restack/NEXT_SERVER_ACTIONS_ENCRYPTION_KEY`. Must be in `.env`
  before the frontend image build (runtime-only injection breaks server actions).
- `RESTACK_ENGINE_MCP_ADDRESS=https://mcp-restack.hodgeluke.com`
  — OpenAI tool calls cannot use localhost.

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
