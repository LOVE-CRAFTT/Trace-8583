"""
Trace-8583 Backend.
Backend for a web-based ledger built on top of an iso_8583 parser project.
"""
# pylint: disable=unused-import

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import select, Session
from .utils import DB_DE_MAPPING, mask_pan, get_raw_json, get_message_base, MessageBaseType
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
from .db import create_db_and_tables, engine
from .iso_8583.iso8583 import iso_8583_to_json as iso_8583

@asynccontextmanager
async def lifespan(app: FastAPI):
    # pylint: disable=unused-argument
    # pylint: disable=redefined-outer-name
    # pylint: disable=missing-function-docstring
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)


@app.post("/{message_string}", response_model=int | None)
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
        with Session(engine) as session:
            match mti:
                case "0200":
                    return insert_financial_request(message_dict, session)
                case "0210":
                    return insert_financial_response(message_dict, session)
                case "0400":
                    return "Reversal Request"
                case "0410":
                    return "Reversal Response"
                case _:
                    return "Different MTI"

    return {None}


def insert_financial_request(request_dict: dict, session: Session) -> int | None:
    """
    Returns id after successful insertion or None if insertion fails
    """
    fin_req_base = FinancialRequestBase(
        **get_message_base(request_dict, MessageBaseType.FIN_REQ_BASE)
        )


    current_pan = fin_req_base.pan_masked
    fin_req_base.pan_masked = mask_pan(current_pan)

    # remove pan from raw_json
    fin_req =FinancialRequest(**fin_req_base.model_dump(),
                         raw_json=get_raw_json(request_dict)
                         )
    session.add(fin_req)
    session.commit()
    session.refresh(fin_req)
    return fin_req.id if fin_req.id else None


def insert_financial_response(response_dict: dict, session: Session) -> int | None:
    """
        Returns id after successful insertion or None if insertion fails
        """

    fin_resp_base = FinancialResponseBase(
        **get_message_base(response_dict, MessageBaseType.FIN_RESP_BASE)
    )
    current_pan = fin_resp_base.pan_masked
    fin_resp_base.pan_masked = mask_pan(current_pan)

    # get the id of the related financial request.
    # using the unique combo
    # stan, terminal_id and loc_txn_date are echoed from the financial response
    stan = fin_resp_base.stan
    terminal_id = fin_resp_base.terminal_id
    loc_txn_date = fin_resp_base.loc_txn_date
    statement = select(FinancialRequest).where(
        FinancialRequest.stan == stan).where(
            FinancialRequest.terminal_id == terminal_id
        ).where(
            FinancialRequest.loc_txn_date == loc_txn_date
        )
    results = session.exec(statement).all()

    # There should be exactly one related fin_req
    # but still insert but related request id would be null
    related_fin_req = results[0] if results else None
    fin_resp =  FinancialResponse(
        **fin_resp_base.model_dump(),
        raw_json=get_raw_json(response_dict),
        request_id=related_fin_req.id if results else None
    )

    session.add(fin_resp)
    session.commit()
    session.refresh(fin_resp)
    return fin_resp.id if fin_resp.id else None
