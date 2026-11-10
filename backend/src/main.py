"""
Trace-8583 Backend.
Backend for a web-based ledger built on top of an iso_8583 parser project.
"""
# pylint: disable=unused-import

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import select, Session
from sqlalchemy import select as sa_select
from .db import create_db_and_tables, get_status_view, engine
from .ingest import process
from .models import FinancialRequest

@asynccontextmanager
async def lifespan(app: FastAPI):
    # pylint: disable=unused-argument
    # pylint: disable=redefined-outer-name
    # pylint: disable=missing-function-docstring
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)


@app.post("/{message_string}", response_model=int | dict[int, str] | None)
def ingest(message_string: str):
    """
     Takes hex string, returns insertion index or parsed JSON or None
    """
    return process(message_string)

@app.get("/transactions", response_model=list[dict])
def get_transactions():
    """
    Pull transactions from the database (transaction_status view)
    """
    return retrieve_txn()

@app.get("/transactions/{txn_idx}", response_model=dict | None)
def get_single_transaction(txn_idx: int):
    """
    Get a single transaction
    """
    return retrieve_txn(idx=txn_idx)


def retrieve_txn(idx: int | None = None):
    """
    Get transaction(s) as a list
    """
    with Session(engine) as session:
        view = get_status_view()

        query = ""
        if idx:
            query = select(FinancialRequest).where(FinancialRequest.id == idx)
        else:
            query = sa_select(view).order_by(view.c.created_at.desc())

        rows = session.exec(query).all()
        if idx:
            if rows:
                return rows[0].model_dump()
            return None

        return [dict(row._mapping) for row in rows] # pylint: disable=protected-access
