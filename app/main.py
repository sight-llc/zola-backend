from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.database import engine, Base
from app.routers import auth, wallet, transfers, kyc


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (dev convenience — use alembic in prod)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Zola Backend",
    description="Thin backend for Zola — auth layer + passthrough to Meroe BaaS infrastructure",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/v1/auth", tags=["Auth"])
app.include_router(wallet.router, prefix="/v1/wallet", tags=["Wallet"])
app.include_router(transfers.router, prefix="/v1/transfers", tags=["Transfers"])
app.include_router(kyc.router, prefix="/v1/kyc", tags=["KYC"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "zola-backend"}
