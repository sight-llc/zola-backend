# Zola Backend

Thin FastAPI + PostgreSQL backend for **Zola** — a consumer wallet app built on top of [Meroe](../nombadva) BaaS infrastructure.

Zola's backend handles **only what Meroe doesn't**: Zola-specific user accounts, JWTs, and light KYC state mirroring. All real banking operations (balances, transactions, payouts) are delegated to Meroe.

---

## Architecture

```
Zola Frontend
     │
     ▼
Zola Backend (this service)
  ├── POST /v1/auth/register  → creates Zola user + provisions Meroe customer + VA
  ├── POST /v1/auth/login     → returns JWT
  ├── GET  /v1/wallet/balance         → proxies Meroe GET /v1/customers/:id/balance
  ├── GET  /v1/wallet/virtual-account → proxies Meroe GET /v1/customers/:id
  ├── GET  /v1/wallet/transactions    → proxies Meroe GET /v1/customers/:id/transactions
  ├── GET  /v1/transfers/banks        → mock (Meroe lookup endpoint pending)
  ├── POST /v1/transfers/resolve      → mock (Meroe lookup endpoint pending)
  ├── POST /v1/transfers/send         → proxies Meroe POST /v1/transfers
  ├── GET  /v1/kyc/status
  ├── POST /v1/kyc/bvn                → proxies Meroe PUT /v1/customers/:id/kyc
  └── POST /v1/kyc/id-document        → demo: auto-promotes to Tier 3
```

---

## Quick start

```bash
# 1. Copy env
cp .env.example .env
# Edit .env — set DATABASE_URL, MEROE_API_KEY, MEROE_BASE_URL, JWT_SECRET

# 2. Install deps
pip install -r requirements.txt

# 3. Run (tables auto-created on startup)
uvicorn app.main:app --reload
```

API docs at: http://localhost:8000/docs

## Deployment (Railway / Render / Fly / any PaaS)

Set the following environment variables on your platform:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Postgres connection string e.g. `postgresql+asyncpg://user:pass@host:5432/zola` |
| `MEROE_BASE_URL` | Meroe API base URL |
| `MEROE_API_KEY` | Your Meroe API key |
| `JWT_SECRET` | Random secret string for signing JWTs |

Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

---

## Endpoints summary

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/auth/register` | Register + provision Meroe customer |
| POST | `/v1/auth/login` | Login → JWT |
| GET | `/v1/auth/me` | Current user info |

### Wallet (JWT required)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/wallet/balance` | Live balance from Meroe |
| GET | `/v1/wallet/virtual-account` | Dedicated NUBAN |
| GET | `/v1/wallet/transactions` | Paginated statement from Meroe |

### Transfers (JWT required)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/transfers/banks` | Bank list (mock) |
| POST | `/v1/transfers/resolve` | Account name lookup (mock) |
| POST | `/v1/transfers/send` | Initiate payout via Meroe |

### KYC (JWT required)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/kyc/status` | Current KYC tier + limits |
| POST | `/v1/kyc/bvn` | Submit BVN → Tier 2 |
| POST | `/v1/kyc/id-document` | Upload ID → Tier 3 |

---

## Connecting to Meroe

Set `MEROE_BASE_URL` and `MEROE_API_KEY` in `.env`. The API key must have scopes:
- `customers:write` — to provision customers
- `customers:read` — for balance / transactions
- `transfers:write` — for payouts

---

## Mock vs Real

| Feature | Status |
|---------|--------|
| Auth (register/login/JWT) | ✅ Real |
| Meroe customer provisioning | ✅ Real |
| Balance | ✅ Real (Meroe) |
| Virtual account | ✅ Real (Meroe) |
| Transactions | ✅ Real (Meroe) |
| Payout initiation | ✅ Real (Meroe) |
| Bank list | 🔶 Mock (Meroe endpoint pending) |
| Account name resolve | 🔶 Mock (Meroe endpoint pending) |
| KYC BVN | ✅ Real (Meroe) |
| KYC ID doc | 🔶 Demo auto-approve |
