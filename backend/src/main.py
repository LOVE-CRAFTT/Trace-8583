"""
Trace-8583 Backend.
Backend for a web-based ledger built on top of an iso_8583 parser project.
"""
# pylint: disable=unused-import

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from .utils import DB_DE_MAPPING, mask_pan
from .models import (OriginalDataElements,
                     FinancialRequest,
                     FinancialResponse,
                     ReversalRequest,
                     ReversalResponse
                     )
from .models import (OriginalDataElementsBase,
                     FinancialRequestBase,
                     FinancialResponseBase,
                     ReversalRequestBase,
                     ReversalResponseBase)
from .db import create_db_and_tables, get_status_view, get_session
from .iso_8583.iso8583 import iso_8583_to_json as iso_8583

@asynccontextmanager
async def lifespan(app: FastAPI):
    # pylint: disable=unused-argument
    # pylint: disable=redefined-outer-name
    # pylint: disable=missing-function-docstring
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)


@app.post("/{message_string}")
def ingest(message_string: str):
    """
     Takes hex string, returns parsed JSON
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



def process(hex_string: str):
    """
    Takes a single hex string and based on the MTI, delegate to appropriate
    database insertion function.
    """
    message_dict = iso_8583(hex_string)
    if message_dict:
        mti = message_dict[0]
        match mti:
            case "0200":
                return insert_financial_request(message_dict)
            case "0210":
                return "Financial Response"
            case "0400":
                return "Reversal Request"
            case "0410":
                return "Reversal Response"
            case _:
                return "Different MTI" # Default fallback

    return {None}


def insert_financial_request(request_dict: dict) -> int | None:
    """
    Returns id after successfu insertion or None
    """
    session = get_session().__next__()

    fin_req_base = FinancialRequestBase(
        pan_masked      = request_dict    [DB_DE_MAPPING["pan_masked"]],
        processing_code = request_dict    [DB_DE_MAPPING["processing_code"]],
        amount          = request_dict    [DB_DE_MAPPING["amount"]],
        transmitted_at  = request_dict    [DB_DE_MAPPING["transmitted_at"]],
        stan            = request_dict    [DB_DE_MAPPING["stan"]],
        loc_txn_time    = request_dict    [DB_DE_MAPPING["loc_txn_time"]],
        loc_txn_date    = request_dict    [DB_DE_MAPPING["loc_txn_date"]],
        rrn             = request_dict.get(DB_DE_MAPPING["rrn"]),
        terminal_id     = request_dict    [DB_DE_MAPPING["terminal_id"]],
        merchant_id     = request_dict    [DB_DE_MAPPING["merchant_id"]],
        currency        = request_dict    [DB_DE_MAPPING["currency"]],
        mcc             = request_dict.get(DB_DE_MAPPING["mcc"]),
        pos_entry_mode  = request_dict.get(DB_DE_MAPPING["pos_entry_mode"]),
        pos_condition   = request_dict.get(DB_DE_MAPPING["pos_condition"]),
        acquirer_id     = request_dict.get(DB_DE_MAPPING["acquirer_id"]),
    )

    current_pan = fin_req_base.pan_masked
    fin_req_base.pan_masked = mask_pan(current_pan)

    # remove pan from raw_json
    fin_req =FinancialRequest(**fin_req_base.model_dump(),
                         raw_json={k: v for k, v in request_dict.items() if k != 2})
    session.add(fin_req)
    session.commit()
    session.refresh(fin_req)
    return fin_req.id if fin_req.id else None
