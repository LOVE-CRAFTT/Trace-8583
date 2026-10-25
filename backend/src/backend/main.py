"""
Trace-8583 Backend.
Backend for a web-based ledger built on top of an iso_8583 parser project.
"""

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from .models import (OriginalDataElements, 
                     FinancialRequest, 
                     FinancialResponse,
                     ReversalRequest,
                     ReversalResponse
                     )
from .db import create_db_and_tables, SessionDep
from .iso_8583.iso8583 import iso_8583_to_json as iso_8583

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)



@app.post("/{message_string}")
def ingest(message_string: str):
    """
     Takes hex string, returns parsed JSON
    """
    val = iso_8583(message_string)
    if val:
        return json.loads(val)
    return {None}

@app.get("/transactions")
def get_transactions():
    """
    Pull transactions from the database
    """

@app.get("/transactios/{txn_id}")
def get_single_transaction(txn_id: int):
    """
    Get a single transaction
    """

if False:
    from sqlmodel import Field, SQLModel

    class Hero(SQLModel, ):
        id: int | None = Field(default=None, primary_key=True)
        name: str = Field(index=True)
        age: int | None = Field(default=None, index=True)
        secret_name: str

    @app.post("/heroes/")
    def create_hero(hero: Hero) -> Hero:
        return hero
