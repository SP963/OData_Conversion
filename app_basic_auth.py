# app_basic_auth.py
import os
import secrets
from typing import List, Optional, Any, Dict
from datetime import date, datetime
from decimal import Decimal

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, validator
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    BigInteger,
    Text,
    Date,
    Numeric,
    select,
    text,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from dotenv import load_dotenv

load_dotenv()

# ---------------------------
# Config & DB
# ---------------------------
DB_HOST = os.getenv("PGHOST", "localhost")
DB_PORT = os.getenv("PGPORT", "5432")
DB_NAME = os.getenv("PGDATABASE", "your_db")
DB_USER = os.getenv("PGUSER", "your_user")
DB_PASSWORD = os.getenv("PGPASSWORD", "your_pass")

DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine: Engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
metadata = MetaData()

trp_table = Table(
    "TRP",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("outlet", Text),
    Column("date", Date),
    Column("day", Text),
    Column("guest_count", Integer),
    Column("category", Text),
    Column("quantity", Integer),
    Column("cost_price", Numeric),
    Column("selling_price", Numeric),
    Column("total_sales", Numeric),
    Column("total_cost_price", Numeric),
    Column("profit", Numeric),
    schema="public",
)

# ---------------------------
# Basic Auth setup
# ---------------------------
security = HTTPBasic()

API_USER = os.getenv("API_BASIC_USER", "admin")
API_PASS = os.getenv("API_BASIC_PASS", "password")


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    correct_user = secrets.compare_digest(credentials.username, API_USER)
    correct_pass = secrets.compare_digest(credentials.password, API_PASS)
    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# ---------------------------
# Pydantic schemas
# ---------------------------
class TRPBase(BaseModel):
    outlet: Optional[str] = None
    date: Optional[date] = None
    day: Optional[str] = None
    guest_count: Optional[int] = None
    category: Optional[str] = None
    quantity: Optional[int] = None
    cost_price: Optional[float] = None
    selling_price: Optional[float] = None
    total_sales: Optional[float] = None
    total_cost_price: Optional[float] = None
    profit: Optional[float] = None

    @validator("date", pre=True)
    def parse_date(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except Exception:
                raise ValueError("date must be YYYY-MM-DD")
        return v


class TRPCreate(TRPBase):
    outlet: str
    date: date
    category: str
    quantity: int


class TRPUpdate(TRPBase):
    pass


class TRPOut(TRPBase):
    id: int

    class Config:
        orm_mode = True


# ---------------------------
# FastAPI app
# ---------------------------
app = FastAPI(title="TRP API (BasicAuth)", version="1.0")

# Production-ready CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# robust row -> dict converter (date -> iso string, Decimal -> float)
def row_to_dict(row) -> Dict[str, Any]:
    # support Row mapping or row proxy
    try:
        mapping = row._mapping  # SQLAlchemy Row in 1.4+
    except Exception:
        try:
            mapping = dict(row)
        except Exception:
            mapping = {}

    out: Dict[str, Any] = {}
    for k, v in mapping.items():
        if isinstance(v, (datetime, date)):
            out[k] = v.isoformat()
        elif isinstance(v, Decimal):
            # Convert Decimal safely to float (or str if precision important)
            out[k] = float(v)
        else:
            out[k] = v
    return out


# helper to fetch a single TRP row by id (no FastAPI deps — pure function)
def fetch_trp_by_id(db_session, item_id: int):
    stmt = select(trp_table).where(trp_table.c.id == item_id)
    r = db_session.execute(stmt).first()
    if not r:
        return None
    return row_to_dict(r)


# ---------------------------
# Routes (all protected by Basic Auth)
# ---------------------------
# Protect all routes by adding dependency param _user=Depends(...) where needed
@app.get("/trp")
def list_trp(limit: int = 100, _user: str = Depends(get_current_username)):
    # use a simple connection to run the select
    with engine.connect() as conn:
        result = conn.execute(
            text('SELECT * FROM public."TRP" LIMIT :lim'), {"lim": limit}
        )
        rows = result.fetchall()
        return [row_to_dict(r) for r in rows]


@app.get("/trp/{item_id}", response_model=TRPOut)
def get_trp(
    item_id: int, db=Depends(get_db), _user: str = Depends(get_current_username)
):
    row = fetch_trp_by_id(db, item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")
    return row


@app.post("/trp", response_model=TRPOut, status_code=201)
def create_trp(
    payload: TRPCreate, db=Depends(get_db), _user: str = Depends(get_current_username)
):
    ins = trp_table.insert().values(
        outlet=payload.outlet,
        date=payload.date,
        day=payload.day,
        guest_count=payload.guest_count,
        category=payload.category,
        quantity=payload.quantity,
        cost_price=payload.cost_price,
        selling_price=payload.selling_price,
        total_sales=payload.total_sales,
        total_cost_price=payload.total_cost_price,
        profit=payload.profit,
    )
    try:
        res = db.execute(ins)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    new_id = res.inserted_primary_key[0]
    row = fetch_trp_by_id(db, new_id)
    if not row:
        raise HTTPException(status_code=500, detail="Failed to fetch created record")
    return row


@app.put("/trp/{item_id}", response_model=TRPOut)
def update_trp(
    item_id: int,
    payload: TRPUpdate,
    db=Depends(get_db),
    _user: str = Depends(get_current_username),
):
    stmt = select(trp_table).where(trp_table.c.id == item_id)
    existing = db.execute(stmt).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Record not found")
    update_values = {k: v for k, v in payload.dict().items() if v is not None}
    if not update_values:
        raise HTTPException(status_code=400, detail="No fields to update")
    upd = trp_table.update().where(trp_table.c.id == item_id).values(**update_values)
    db.execute(upd)
    db.commit()
    row = fetch_trp_by_id(db, item_id)
    return row


@app.delete("/trp/{item_id}", status_code=204)
def delete_trp(
    item_id: int, db=Depends(get_db), _user: str = Depends(get_current_username)
):
    stmt = select(trp_table).where(trp_table.c.id == item_id)
    existing = db.execute(stmt).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Record not found")
    db.execute(trp_table.delete().where(trp_table.c.id == item_id))
    db.commit()
    return None


@app.get("/health")
def health(db=Depends(get_db), _user: str = Depends(get_current_username)):
    try:
        with engine.connect() as conn:
            conn.execute(select(trp_table.c.id).limit(1))
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Unauthenticated health check for load balancers
@app.get("/health-check")
def health_check_no_auth():
    """Simple health check without authentication for load balancers/monitoring"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "service": "trp-api"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 503


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app_basic_auth:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENV", "production") != "production",
        log_level=os.getenv("LOG_LEVEL", "info"),
    )
