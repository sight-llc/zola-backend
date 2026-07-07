# Zola Backend

**FastAPI backend for Zola — Banking built for you.**

A thin, focused FastAPI + PostgreSQL backend that orchestrates user authentication, session management, and proxies banking operations to [Meroe](https://github.com/sight-llc/nombadva). Zola Backend handles only what Meroe doesn't: user accounts, JWTs, and light KYC state mirroring.

---

## Live Demo

- **Live Backend:** https://zola-backend.fastapicloud.dev
- **API Documentation:** https://zola-backend.fastapicloud.dev/docs

---

## What is Zola Backend?

Zola Backend is the middle layer between the Zola Frontend and Meroe banking infrastructure. It provides:

- **User Authentication** — Email/password registration and JWT-based login
- **Session Management** — Token issuance and validation
- **KYC State Mirroring** — Lightweight KYC status tracking
- **API Orchestration** — Proxies requests to Meroe with proper authentication
- **User Context** — Maps Meroe customer IDs to Zola user accounts

**What it doesn't do:** Zola Backend does NOT handle banking operations directly. All financial operations (balances, transactions, virtual accounts, payouts) are delegated to Meroe.

---

## Architecture

```
┌─────────────────┐
│  Zola Frontend  │
│  (React/TS)     │
└────────┬────────┘
         │
         │ HTTP/REST
         │ JWT Auth
         ▼
┌─────────────────────────────────────────┐
│         Zola Backend (this service)     │
│                                         │
│  Responsibilities:                      │
│  • User registration & login            │
│  • JWT token management                 │
│  • Session persistence                  │
│  • KYC state mirroring                  │
│  • Proxying to Meroe                    │
└────────┬────────────────────────────────┘
         │
         │ Proxied requests
         │ (with Meroe API key)
         ▼
┌─────────────────────────────────────────┐
│              Meroe                      │
│  (Banking Infrastructure)               │
│                                         │
│  • Virtual account provisioning         │
│  • Balance & transactions               │
│  • Payouts with maker-checker           │
│  • Webhooks                             │
│  • Security & compliance                │
└─────────────────────────────────────────┘
```

---

## Why This Approach?

### Separation of Concerns

| Layer | Responsibility | Why |
|-------|---------------|-----|
| **Zola Frontend** | User interface, UX | User experience |
| **Zola Backend** | Auth, sessions, orchestration | User management, security |
| **Meroe** | Banking operations, compliance | Financial infrastructure |

### Benefits

1. **Simplified Auth** — Zola Backend handles user-friendly email/password auth, while Meroe handles the banking customer lifecycle
2. **Flexibility** — Swap or upgrade Meroe without changing frontend code
3. **Security** — Meroe API key never exposed to frontend
4. **Lightweight** — Zola Backend is ~500 lines of code vs. thousands for full banking logic
5. **Rapid Development** — Focus on UX, not banking infrastructure

---

## Tech Stack

| Technology | Purpose |
|-----------|---------|
| **FastAPI** | Modern, fast Python web framework |
| **Python 3.10+** | Programming language |
| **PostgreSQL 16** | Primary database |
| **SQLAlchemy 2.0** | ORM for database operations |
| **Alembic** | Database migrations |
| **Pydantic** | Data validation |
| **python-jose** | JWT token handling |
| **passlib** | Password hashing |
| **python-multipart** | File uploads (ID documents) |
| **httpx** | Async HTTP client for Meroe proxying |

---

## Project Structure

```
zola-backend/
├── app/
│   ├── main.py              # FastAPI app initialization
│   ├── config.py            # Environment configuration
│   ├── database.py          # Database connection
│   │
│   ├── models/              # SQLAlchemy models
│   │   ├── user.py         # User model
│   │   └── ...
│   │
│   ├── routes/              # API endpoints
│   │   ├── auth.py         # Login, register, PIN
│   │   ├── wallet.py       # Balance, VA, transactions
│   │   ├── transfers.py    # Banks, resolve, send
│   │   └── kyc.py          # KYC status, BVN, ID upload
│   │
│   ├── schemas/             # Pydantic schemas
│   │   ├── user.py
│   │   ├── wallet.py
│   │   └── ...
│   │
│   ├── services/            # Business logic
│   │   ├── meroe_client.py # Meroe API client
│   │   └── ...
│   │
│   └── utils/               # Helpers
│       ├── security.py     # JWT, password hashing
│       └── ...
│
├── alembic/                 # Database migrations
│   ├── versions/
│   └── env.py
│
├── tests/                   # Test suite
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
├── alembic.ini             # Alembic configuration
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- PostgreSQL 16
- Meroe running on `http://localhost:8081` (or your Meroe instance)
- Meroe API key

### Installation

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# Copy environment file
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/zola

# Meroe Connection
MEROE_BASE_URL=http://localhost:8081
MEROE_API_KEY=your_meroe_api_key_here

# JWT
JWT_SECRET=your_jwt_secret_key_here_min_32_chars
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440
```

### Database Setup

```bash
# Run migrations
alembic upgrade head
```

### Running the Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload

# Or with custom host/port
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

**Interactive API Docs:** http://localhost:8000/docs

**Alternative docs:** http://localhost:8000/redoc

---

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/auth/register` | Register new user + provision Meroe customer |
| POST | `/v1/auth/login` | Login with email/password |
| GET | `/v1/auth/me` | Get current user info |
| POST | `/v1/auth/pin` | Set transaction PIN |

### Wallet (JWT Required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/wallet/balance` | Get wallet balance (from Meroe) |
| GET | `/v1/wallet/virtual-account` | Get dedicated NUBAN (from Meroe) |
| GET | `/v1/wallet/transactions` | Get transaction history (from Meroe) |

### Transfers (JWT Required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/transfers/banks` | Get list of banks |
| POST | `/v1/transfers/resolve` | Resolve account name by bank code + account number |
| POST | `/v1/transfers/send` | Send money to external account (via Meroe) |

### KYC (JWT Required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/kyc/status` | Get current KYC tier and limits |
| POST | `/v1/kyc/bvn` | Submit BVN for verification (via Meroe) |
| POST | `/v1/kyc/id-document` | Upload ID document |

---

## How It Works

### User Registration Flow

```
1. Frontend sends: POST /v1/auth/register
   { name, email, password, phone }

2. Zola Backend:
   - Creates user in PostgreSQL
   - Hashes password with BCrypt
   - Calls Meroe: POST /v1/customers (provisions banking customer)
   - Stores Meroe customer_id
   - Generates JWT token
   - Returns: { access_token, user }

3. Frontend stores JWT and user data
```

### Balance Check Flow

```
1. Frontend sends: GET /v1/wallet/balance
   Headers: Authorization: Bearer <jwt>

2. Zola Backend:
   - Validates JWT
   - Extracts Meroe customer_id from user
   - Calls Meroe: GET /v1/customers/:id/balance
   - Returns balance to frontend

3. Frontend displays balance
```

### Send Money Flow

```
1. Frontend sends: POST /v1/transfers/send
   { bankCode, accountNumber, accountName, amount, narration, pin }

2. Zola Backend:
   - Validates JWT
   - Verifies transaction PIN
   - Calls Meroe: POST /v1/transfers
   - Returns transfer reference

3. Meroe processes payout with maker-checker if needed
4. Webhook sent to Meroe when transfer completes
```

---

## Meroe Integration

Zola Backend acts as a **thin proxy** to Meroe. All banking operations are delegated:

| Zola Backend | Meroe | Purpose |
|-------------|-------|---------|
| `POST /v1/auth/register` | `POST /v1/customers` | Provision customer + VA |
| `GET /v1/wallet/balance` | `GET /v1/customers/:id/balance` | Live balance |
| `GET /v1/wallet/virtual-account` | `GET /v1/customers/:id` | NUBAN details |
| `GET /v1/wallet/transactions` | `GET /v1/customers/:id/transactions` | Statement |
| `POST /v1/transfers/send` | `POST /v1/transfers` | Payout |
| `POST /v1/kyc/bvn` | `PUT /v1/customers/:id/kyc` | BVN update |

**Authentication to Meroe:** Uses `MEROE_API_KEY` in the `Authorization` header.

---

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    meroe_customer_id VARCHAR(255) UNIQUE,
    pin_hash VARCHAR(255),
    kyc_tier INTEGER DEFAULT 1,
    bvn_verified BOOLEAN DEFAULT FALSE,
    id_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest

# With coverage
pytest --cov=app
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Code Style

```bash
# Format with Black
black app/

# Lint with Ruff
ruff check app/
```

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `MEROE_BASE_URL` | Meroe API base URL | Yes |
| `MEROE_API_KEY` | Meroe API key | Yes |
| `JWT_SECRET` | Secret for JWT signing (min 32 chars) | Yes |
| `JWT_ALGORITHM` | JWT signing algorithm | No (default: HS256) |
| `JWT_EXPIRATION_MINUTES` | Token expiration time | No (default: 1440) |

---

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables (Production)

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/zola
MEROE_BASE_URL=https://meroe.example.com
MEROE_API_KEY=prod_api_key
JWT_SECRET=secure_random_secret_key
```

### Start Command

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

## Security Considerations

1. **JWT Secret** — Use a strong, random secret (min 32 characters)
2. **Meroe API Key** — Never expose to frontend, store in environment variables
3. **Password Hashing** — BCrypt with cost factor 12
4. **HTTPS** — Always use HTTPS in production
5. **CORS** — Configure CORS to allow only your frontend domain
6. **Rate Limiting** — Implement rate limiting for production (via Meroe or reverse proxy)

---

## Troubleshooting

### Meroe Connection Issues

```bash
# Test Meroe connectivity
curl http://localhost:8081/actuator/health

# Check Meroe API key
curl -H "Authorization: Bearer $MEROE_API_KEY" http://localhost:8081/v3/api-docs
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
psql -U postgres -c "SELECT 1"

# Check database exists
psql -U postgres -l | grep zola
```

### JWT Token Issues

- Ensure `JWT_SECRET` is at least 32 characters
- Check token expiration (default: 24 hours)
- Verify token is sent in `Authorization: Bearer <token>` header

---

## Related Projects

- **[Zola Frontend](../../../zola-frontend)** — React frontend application
- **[Meroe](../../../nombadva)** — Banking infrastructure (formerly NombaVault)

---

## License

MIT

---

## Team

Part of the Zola project — demonstrating rapid financial application development with Meroe.
