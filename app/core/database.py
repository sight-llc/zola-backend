from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings
import uuid
from sqlalchemy.pool import NullPool


settings = get_settings()



engine = create_async_engine(
    settings.database_url,
    poolclass=NullPool,
    connect_args={
        "statement_cache_size": 0,
    },
)

# engine = create_async_engine(
#     settings.database_url,
#     echo=False,
#     pool_pre_ping=True,
#     connect_args={
#         "statement_cache_size": 0,
#         "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",
#     },
# )
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
