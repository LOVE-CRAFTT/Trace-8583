"""
Trace-8583 Backend.
Backend for a web-based ledger built on top of an iso_8583 parser project.
"""
# pylint: disable=unused-import

from contextlib import asynccontextmanager

from fastapi import FastAPI
from .db import create_db_and_tables
from .ingest import process

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

@app.get("/transactions")
def get_transactions():
    """
    Pull transactions from the database (transaction_status view)
    """

@app.get("/transactios/{txn_id}")
def get_single_transaction(txn_id: int): # pylint: disable=unused-argument
    """
    Get a single transaction
    """
