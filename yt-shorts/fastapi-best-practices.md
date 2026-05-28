# FastAPI Best Practices Guide

A comprehensive guide based on the [benavlabs/FastAPI-boilerplate](https://github.com/benavlabs/FastAPI-boilerplate) — a production-proven, batteries-included async API starter with 1.8k+ GitHub stars.

## Table of Contents

1. [Project Structure](#project-structure)
2. [Environment Configuration](#environment-configuration)
3. [Database Integration](#database-integration)
4. [Models & Schemas](#models--schemas)
5. [CRUD Operations](#crud-operations)
6. [API Endpoints & Versioning](#api-endpoints--versioning)
7. [Authentication & Security](#authentication--security)
8. [Caching with Redis](#caching-with-redis)
9. [Background Tasks](#background-tasks)
10. [Rate Limiting](#rate-limiting)
11. [Error Handling](#error-handling)
12. [Performance Optimization](#performance-optimization)
13. [Testing Strategies](#testing-strategies)
14. [Deployment Guidelines](#deployment-guidelines)
15. [Common Pitfalls and Solutions](#common-pitfalls-and-solutions)

---

## Project Structure

### Recommended Directory Layout

```
FastAPI-boilerplate/
├── Dockerfile                    # Container configuration
├── docker-compose.yml            # Multi-service orchestration
├── pyproject.toml                # Project config and dependencies
├── uv.lock                       # Locked dependency versions
├── .env                          # Environment variables (never commit)
├── .env.example                  # Template for required vars (commit this)
├── tests/                        # Test suite
│   ├── conftest.py               # Pytest configuration and fixtures
│   ├── helpers/
│   │   ├── generators.py         # Test data generators
│   │   └── mocks.py              # Mock objects and functions
│   └── test_user_unit.py         # Feature unit tests
└── src/
    ├── app/                      # Main application package
    │   ├── main.py               # FastAPI app entry point
    │   ├── api/                  # API layer
    │   │   ├── dependencies.py   # Shared dependencies
    │   │   └── v1/               # Versioned endpoints
    │   │       ├── login.py
    │   │       ├── users.py
    │   │       ├── posts.py
    │   │       └── tasks.py
    │   ├── core/                 # Core utilities and config
    │   │   ├── config.py         # Settings (Pydantic BaseSettings)
    │   │   ├── logger.py         # Logging setup
    │   │   ├── security.py       # JWT, hashing utilities
    │   │   ├── setup.py          # App factory
    │   │   ├── db/               # DB connection & session
    │   │   ├── exceptions/       # Custom exceptions
    │   │   ├── utils/            # Shared utilities
    │   │   └── worker/           # ARQ background worker
    │   ├── models/               # SQLAlchemy ORM models
    │   ├── schemas/              # Pydantic request/response schemas
    │   ├── crud/                 # Database operations (FastCRUD)
    │   └── middleware/           # Custom middleware
    ├── migrations/               # Alembic migrations
    │   ├── env.py
    │   ├── script.py.mako
    │   └── versions/
    └── scripts/                  # Init/maintenance scripts
        ├── create_first_superuser.py
        └── create_first_tier.py
```

### Data Flow

Every request flows through clean layers — never skip them:

```
Request → API Endpoint → Dependencies → CRUD → Model → Database
Response ← API Response ← Schema ← CRUD ← Query Result ← Database
```

### Key Principles

- **Layered Architecture**: API → CRUD → Models — each layer has one job
- **Separation of Concerns**: No DB logic in endpoints, no HTTP logic in CRUD
- **Async First**: Every function touching I/O must be `async def`
- **Type Safety**: Pydantic V2 schemas on all inputs and outputs
- **Centralized Config**: All settings in `core/config.py`, never scattered

---

## Environment Configuration

### Variable Strategy

```bash
# .env (never commit - add to .gitignore)
# App
APP_NAME="My FastAPI App"
APP_DESCRIPTION="API for my app"
APP_VERSION="0.1.0"
ENVIRONMENT=local          # local | staging | production
SECRET_KEY=changeme-use-openssl-rand-hex-32

# Database
POSTGRES_USER=myuser
POSTGRES_PASSWORD=mypassword
POSTGRES_DB=mydb
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# First admin user
ADMIN_NAME=Admin
ADMIN_EMAIL=admin@example.com
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme
```

### Settings with Pydantic BaseSettings

Centralize all config in `core/config.py` — never call `os.environ` directly anywhere else:

```python
# src/app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import AnyUrl, field_validator

class Settings(BaseSettings):
    # App
    APP_NAME: str = "FastAPI App"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "local"
    DEBUG: bool = False

    # Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # Computed DB URL
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Docs — only expose in non-production
    @property
    def DOCS_URL(self) -> str | None:
        return "/docs" if self.ENVIRONMENT != "production" else None

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### Environment-Specific Behavior

```python
# Disable docs in production automatically
app = FastAPI(
    title=settings.APP_NAME,
    docs_url=settings.DOCS_URL,        # None in production
    redoc_url=settings.DOCS_URL,
)
```

---

## Database Integration

### Async SQLAlchemy Setup

```python
# src/app/core/db/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,         # Verify connections before use
    echo=settings.ENVIRONMENT == "local",
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,     # Avoid lazy loading after commit
    autocommit=False,
    autoflush=False,
)

class Base(DeclarativeBase):
    pass

# Dependency for FastAPI endpoints
async def async_get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### Base Model with Common Fields

```python
# src/app/core/db/models.py
from datetime import datetime, UTC
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db.database import Base

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
```

### Migration Commands

```bash
# Generate a new migration from model changes
cd src && uv run alembic revision --autogenerate -m "add user table"

# Apply all pending migrations
cd src && uv run alembic upgrade head

# Roll back one migration
cd src && uv run alembic downgrade -1

# View current migration state
cd src && uv run alembic current
```

---

## Models & Schemas

### SQLAlchemy Model

```python
# src/app/models/user.py
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db.database import Base
from app.core.db.models import TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    posts: Mapped[list["Post"]] = relationship("Post", back_populates="author", lazy="selectin")
```

### Pydantic V2 Schemas

Keep schemas separate from models. Define schemas for each use case:

```python
# src/app/schemas/user.py
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from datetime import datetime

# Base - shared fields
class UserBase(BaseModel):
    name: str
    username: str
    email: EmailStr

# Create - fields needed to create
class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

# Update - all optional for partial updates
class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    password: str | None = None

# Read - what the API returns (no password!)
class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime

# Internal - includes hashed_password for internal use only
class UserInDB(UserRead):
    hashed_password: str
```

### Schema Rules

- **Never return** `hashed_password` or sensitive fields in `Read` schemas
- **Always use** `model_config = ConfigDict(from_attributes=True)` on Read schemas
- **Use `EmailStr`** for email validation — don't write your own regex
- **Create separate schemas** per use case — don't reuse Create for Update

---

## CRUD Operations

### Base CRUD Pattern

```python
# src/app/crud/crud_base.py
from typing import Any, Generic, TypeVar
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db.database import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: int) -> ModelType | None:
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> list[ModelType]:
        result = await db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        db_obj = self.model(**obj_in.model_dump())
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: ModelType, obj_in: UpdateSchemaType | dict[str, Any]
    ) -> ModelType:
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> ModelType | None:
        obj = await self.get(db, id=id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj

    async def count(self, db: AsyncSession) -> int:
        result = await db.execute(select(func.count()).select_from(self.model))
        return result.scalar_one()
```

### Feature-Specific CRUD

```python
# src/app/crud/crud_users.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_password_hash, verify_password
from app.crud.crud_base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):

    async def get_by_email(self, db: AsyncSession, *, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, db: AsyncSession, *, username: str) -> User | None:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        data = obj_in.model_dump()
        data["hashed_password"] = get_password_hash(data.pop("password"))
        db_obj = User(**data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def authenticate(
        self, db: AsyncSession, *, email: str, password: str
    ) -> User | None:
        user = await self.get_by_email(db, email=email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

crud_users = CRUDUser(User)
```

---

## API Endpoints & Versioning

### Versioned Router Structure

```python
# src/app/api/v1/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_current_user, get_current_superuser
from app.core.db.database import async_get_db
from app.crud.crud_users import crud_users
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.models.user import User

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserRead)
async def read_current_user(
    current_user: User = Depends(get_current_user),
) -> UserRead:
    return current_user

@router.get("/{user_id}", response_model=UserRead)
async def read_user(
    user_id: int,
    db: AsyncSession = Depends(async_get_db),
    _: User = Depends(get_current_superuser),  # Superuser only
) -> UserRead:
    user = await crud_users.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(async_get_db),
) -> UserRead:
    existing = await crud_users.get_by_email(db, email=user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    return await crud_users.create(db, obj_in=user_in)

@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    user = await crud_users.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return await crud_users.update(db, db_obj=user, obj_in=user_in)
```

### App Factory & Router Registration

```python
# src/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import users, posts, login, tasks

def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url=settings.DOCS_URL,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    api_prefix = "/api/v1"
    app.include_router(login.router, prefix=api_prefix)
    app.include_router(users.router, prefix=api_prefix)
    app.include_router(posts.router, prefix=api_prefix)
    app.include_router(tasks.router, prefix=api_prefix)

    return app

app = create_application()
```

### Pagination Pattern

Always paginate list endpoints — never return unbounded lists:

```python
from fastapi import Query
from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool

@router.get("/", response_model=PaginatedResponse[UserRead])
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(async_get_db),
) -> PaginatedResponse[UserRead]:
    skip = (page - 1) * page_size
    users = await crud_users.get_multi(db, skip=skip, limit=page_size)
    total = await crud_users.count(db)
    return PaginatedResponse(
        data=users,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(skip + page_size) < total,
    )
```

---

## Authentication & Security

### JWT Token Flow

```python
# src/app/core/security.py
from datetime import datetime, timedelta, UTC
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(subject: str | int) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(subject), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(subject: str | int) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
```

### Auth Dependencies

```python
# src/app/api/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db.database import async_get_db
from app.core.security import decode_token
from app.crud.crud_users import crud_users
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login/access-token")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(async_get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await crud_users.get(db, id=int(user_id))
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

async def get_current_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")
    return current_user
```

---

## Caching with Redis

### Decorator-Based Caching

```python
# src/app/core/utils/cache.py
import json
import functools
from typing import Callable, Any
import redis.asyncio as aioredis
from app.core.config import settings

redis_client = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

def cache(expire: int = 60, prefix: str = "cache"):
    """Decorator to cache endpoint responses in Redis."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Build cache key from function name and arguments
            cache_key = f"{prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"

            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

            result = await func(*args, **kwargs)
            await redis_client.setex(cache_key, expire, json.dumps(result, default=str))
            return result
        return wrapper
    return decorator

async def invalidate_cache(pattern: str) -> int:
    """Delete all keys matching a pattern."""
    keys = await redis_client.keys(pattern)
    if keys:
        return await redis_client.delete(*keys)
    return 0
```

### Cache Usage

```python
@router.get("/posts", response_model=list[PostRead])
@cache(expire=300, prefix="posts")        # Cache for 5 minutes
async def list_posts(db: AsyncSession = Depends(async_get_db)) -> list[PostRead]:
    return await crud_posts.get_multi(db)

# Invalidate on create/update/delete
@router.post("/posts", response_model=PostRead, status_code=201)
async def create_post(post_in: PostCreate, db: AsyncSession = Depends(async_get_db)):
    post = await crud_posts.create(db, obj_in=post_in)
    await invalidate_cache("posts:list_posts:*")    # Clear related cache
    return post
```

---

## Background Tasks

### ARQ Worker Setup

```python
# src/app/core/worker/functions.py
from arq.connections import RedisSettings
from app.core.config import settings

# Define background task functions
async def send_email_task(ctx: dict, to: str, subject: str, body: str) -> dict:
    """Send an email in the background."""
    # Your email sending logic here
    print(f"Sending email to {to}: {subject}")
    return {"status": "sent", "to": to}

async def generate_report_task(ctx: dict, report_id: int) -> dict:
    """Generate a heavy report in the background."""
    # Your report generation logic here
    return {"status": "generated", "report_id": report_id}

# Worker settings
class WorkerSettings:
    functions = [send_email_task, generate_report_task]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 300   # 5 minute timeout per job
```

### Enqueuing Jobs from Endpoints

```python
# src/app/core/utils/queue.py
from arq import create_pool
from arq.connections import RedisSettings
from app.core.config import settings

async def get_redis_pool():
    return await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))

# In your endpoint
@router.post("/users/{user_id}/welcome-email")
async def send_welcome_email(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
) -> dict:
    pool = await get_redis_pool()
    job = await pool.enqueue_job("send_email_task", to=current_user.email, subject="Welcome!")
    return {"job_id": job.job_id, "status": "queued"}
```

---

## Rate Limiting

### Per-Tier Rate Limits

```python
# src/app/core/utils/rate_limit.py
from fastapi import Request, HTTPException, status
from app.core.config import settings
import redis.asyncio as aioredis

redis_client = aioredis.from_url(settings.REDIS_URL)

async def rate_limiter(
    request: Request,
    max_requests: int = 100,
    window_seconds: int = 60,
):
    """Sliding window rate limiter using Redis."""
    client_ip = request.client.host
    key = f"rate_limit:{client_ip}:{request.url.path}"

    pipe = redis_client.pipeline()
    now = asyncio.get_event_loop().time()
    window_start = now - window_seconds

    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zcard(key)
    pipe.zadd(key, {str(now): now})
    pipe.expire(key, window_seconds)
    results = await pipe.execute()

    request_count = results[1]
    if request_count >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {max_requests} requests per {window_seconds}s",
            headers={"Retry-After": str(window_seconds)},
        )

# Usage as dependency
from functools import partial

rate_limit_10 = partial(rate_limiter, max_requests=10, window_seconds=60)   # Strict
rate_limit_100 = partial(rate_limiter, max_requests=100, window_seconds=60) # Normal

@router.post("/login", dependencies=[Depends(rate_limit_10)])
async def login(...): ...

@router.get("/posts", dependencies=[Depends(rate_limit_100)])
async def list_posts(...): ...
```

---

## Error Handling

### Custom Exception Classes

```python
# src/app/core/exceptions/http_exceptions.py
from fastapi import HTTPException, status

class NotFoundException(HTTPException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class UnauthorizedException(HTTPException):
    def __init__(self, detail: str = "Not authenticated"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

class ForbiddenException(HTTPException):
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class DuplicateValueException(HTTPException):
    def __init__(self, detail: str = "Value already exists"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
```

### Global Exception Handlers

```python
# src/app/main.py (inside create_application)
from fastapi.responses import JSONResponse
from fastapi import Request
from sqlalchemy.exc import IntegrityError

@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Database integrity error — duplicate value or constraint violation"},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Log the error
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )
```

### Structured Logging

```python
# src/app/core/logger.py
import logging
import sys
from app.core.config import settings

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if settings.ENVIRONMENT == "local" else logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

logger = setup_logger("app")
```

---

## Performance Optimization

### Async Rules

Always use `async def` for any function that touches I/O:

```python
# ✅ Correct — async for all I/O
@router.get("/users")
async def list_users(db: AsyncSession = Depends(async_get_db)):
    return await crud_users.get_multi(db)

# ❌ Wrong — sync route blocks the event loop
@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    return crud_users.get_multi(db)
```

### Query Optimization

Use `selectinload` or `joinedload` to avoid N+1 queries:

```python
from sqlalchemy.orm import selectinload

async def get_user_with_posts(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.posts))   # Load posts in a single extra query
    )
    return result.scalar_one_or_none()
```

### Connection Pooling

Tune pool settings based on your workload:

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,           # Persistent connections
    max_overflow=20,        # Temporary extra connections
    pool_timeout=30,        # Wait before giving up
    pool_recycle=1800,      # Recycle connections after 30 min
    pool_pre_ping=True,     # Test connection before using
)
```

---

## Testing Strategies

### Pytest Configuration

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.main import app
from app.core.db.database import Base, async_get_db

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(test_engine):
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()   # Always roll back after each test

@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[async_get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

### Test Helpers

```python
# tests/helpers/generators.py
from app.schemas.user import UserCreate

def generate_user_data(suffix: str = "test") -> dict:
    return {
        "name": f"Test User {suffix}",
        "username": f"testuser_{suffix}",
        "email": f"testuser_{suffix}@example.com",
        "password": "Password123!",
    }
```

### Unit Tests

```python
# tests/test_user_unit.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    response = await client.post("/api/v1/users/", json={
        "name": "Test User",
        "username": "testuser",
        "email": "test@example.com",
        "password": "Password123!",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "hashed_password" not in data          # Sensitive field not exposed

@pytest.mark.asyncio
async def test_duplicate_email_rejected(client: AsyncClient):
    user_data = {
        "name": "User",
        "username": "user1",
        "email": "dupe@example.com",
        "password": "Password123!",
    }
    await client.post("/api/v1/users/", json=user_data)

    response = await client.post("/api/v1/users/", json={**user_data, "username": "user2"})
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_get_user_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/users/1")
    assert response.status_code == 401
```

### Test Commands

```bash
uv run pytest                          # Run all tests
uv run pytest -v                       # Verbose output
uv run pytest --cov=src/app            # With coverage
uv run pytest tests/test_user_unit.py  # Single file
uv run pytest -k "test_create"         # Tests matching pattern
```

---

## Deployment Guidelines

### Quickstart

```bash
# Clone and setup
git clone https://github.com/benavlabs/FastAPI-boilerplate
cd FastAPI-boilerplate

# Interactive setup — picks local/staging/production config
./setup.py
```

### Three Deployment Modes

**Local development:**
```bash
./setup.py local
docker compose up           # Uvicorn with auto-reload
```

**Staging (Gunicorn + Uvicorn workers):**
```bash
./setup.py staging
docker compose up
```

**Production (NGINX + Gunicorn + Uvicorn workers):**
```bash
./setup.py production
# ⚠️ Change SECRET_KEY and all passwords in .env first!
docker compose up -d
```

### Multi-Stage Dockerfile

```dockerfile
# Dockerfile
FROM python:3.12-slim AS base
RUN pip install uv

FROM base AS deps
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM base AS runner
WORKDIR /app
COPY --from=deps /app/.venv ./.venv
COPY src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

CMD ["gunicorn", "src.app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000"]
```

### Docker Compose (Production)

```yaml
# docker-compose.yml
services:
  app:
    build: .
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - ENVIRONMENT=production
    env_file:
      - .env
    ports:
      - "8000:8000"

  worker:
    build: .
    command: uv run arq src.app.core.worker.functions.WorkerSettings
    depends_on:
      - redis
    env_file:
      - .env

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      retries: 5

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./default.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - app

volumes:
  postgres_data:
  redis_data:
```

### Health Check Endpoint

```python
# src/app/api/v1/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.db.database import async_get_db
import redis.asyncio as aioredis
from app.core.config import settings

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check(db: AsyncSession = Depends(async_get_db)) -> dict:
    checks = {}

    # Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # Redis check
    try:
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"

    status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}
```

---

## Common Pitfalls and Solutions

### 1. Sync Code Inside Async Routes

**Problem**: Using sync database calls or `requests` library inside `async def` blocks the event loop.

**Solution**: Always use async drivers and async HTTP clients:

```python
# ❌ Blocks the event loop
import requests
async def fetch_data():
    return requests.get("https://api.example.com")

# ✅ Non-blocking
import httpx
async def fetch_data():
    async with httpx.AsyncClient() as client:
        return await client.get("https://api.example.com")
```

### 2. N+1 Query Problem

**Problem**: Accessing relationships in a loop triggers one query per iteration.

**Solution**: Use `selectinload` or `joinedload` at query time:

```python
# ❌ Causes N+1 queries
users = await crud_users.get_multi(db)
for user in users:
    print(user.posts)    # Each access fires a new query

# ✅ Load relationships upfront
result = await db.execute(
    select(User).options(selectinload(User.posts))
)
users = result.scalars().all()
```

### 3. Returning Sensitive Fields

**Problem**: Accidentally including `hashed_password`, tokens, or internal IDs in API responses.

**Solution**: Always use dedicated `Read` schemas that explicitly exclude sensitive fields:

```python
# ❌ Never return the model directly
return user            # Includes hashed_password

# ✅ Return via Read schema
return UserRead.model_validate(user)
```

### 4. Missing Database Indexes

**Problem**: Queries on `email`, `username`, or foreign keys are slow without indexes.

**Solution**: Always add `index=True` on columns used in `WHERE` clauses:

```python
# ✅ Add indexes on lookup fields
email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
```

### 5. Not Validating on Update

**Problem**: `PATCH` endpoints accepting partial data skip validation, allowing empty strings or invalid values.

**Solution**: Use `model_dump(exclude_unset=True)` for partial updates and validate in the schema:

```python
class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None    # EmailStr still validates if provided

# In CRUD
update_data = obj_in.model_dump(exclude_unset=True)  # Only update what's sent
```

### 6. Exposing Docs in Production

**Problem**: Swagger UI (`/docs`) exposed in production leaks API structure.

**Solution**: Control with environment variable:

```python
docs_url = "/docs" if settings.ENVIRONMENT != "production" else None
app = FastAPI(docs_url=docs_url, redoc_url=docs_url)
```

---

## Conclusion

The `benavlabs/FastAPI-boilerplate` gives you a production-proven foundation for building async Python APIs. Following these practices ensures your APIs are secure, fast, and maintainable from day one. Key takeaways:

- Always use `async def` for any function touching I/O — never mix sync and async
- Validate all inputs with Pydantic V2 schemas — never trust raw request data
- Use dedicated Read schemas — never return ORM models directly to clients
- Centralize all config in `core/config.py` using `BaseSettings`
- Version your API from day one — `/api/v1/` makes future changes painless
- Add indexes on all columns used in WHERE clauses
- Paginate all list endpoints — never return unbounded results
- Invalidate caches after mutations — stale cache is worse than no cache
- Test against a real (but isolated) database — not mocks of your ORM

See the [official docs](https://benavlabs.github.io/FastAPI-boilerplate/) and [FastAPI docs](https://fastapi.tiangolo.com) for more.
