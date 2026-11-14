"""
Trace-8583 Backend.
Backend for a web-based ledger built on top of an iso_8583 parser project.
"""
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import create_db_and_tables
from .ingest import process
from .retrieve_txn import retrieve_txn
from .generator import start_generator, stop_generator

@asynccontextmanager
async def lifespan(app: FastAPI):
    # pylint: disable=unused-argument
    # pylint: disable=redefined-outer-name
    # pylint: disable=missing-function-docstring
    create_db_and_tables()

    # start generator
    load_dotenv()
    use_generator = os.getenv("USE_GENERATOR") == "TRUE"
    if use_generator:
        start_generator()

    yield

    # shutdown generator
    if use_generator:
        stop_generator()

app = FastAPI(lifespan=lifespan)

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
