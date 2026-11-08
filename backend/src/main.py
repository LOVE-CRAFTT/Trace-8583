"""
Trace-8583 Backend.
Backend for a web-based ledger built on top of an iso_8583 parser project.
"""
# pylint: disable=unused-import

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import select, Session
from .utils import (mask_pan, 
                    get_raw_json, 
                    get_message_base, 
                    MessageBaseType,
                    get_ode_base
                    )
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
                    return insert_reversal_request(message_dict, session)
                case "0410":
                    return "Reversal Response"
                case _:
                    return "Different MTI"

    return {None}


def insert_financial_request(request_dict: dict[int, str], session: Session) -> int | None:
    """
    Returns id after successful insertion or None if insertion fails
    """
    fin_req_base = FinancialRequestBase(
        **get_message_base(request_dict, MessageBaseType.FIN_REQ_BASE)
        )
    fin_req_base.pan = mask_pan(fin_req_base.pan)

    # remove pan from raw_json
    fin_req =FinancialRequest(**fin_req_base.model_dump(),
                         raw_json=get_raw_json(request_dict)
                         )
    session.add(fin_req)
    session.commit()
    session.refresh(fin_req)
    return fin_req.id if fin_req.id else None


def insert_financial_response(response_dict: dict[int, str], session: Session) -> int | None:
    """
    Returns id after successful insertion or None if insertion fails
    """

    fin_resp_base = FinancialResponseBase(
        **get_message_base(response_dict, MessageBaseType.FIN_RESP_BASE)
    )
    fin_resp_base.pan = mask_pan(fin_resp_base.pan)

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


def insert_reversal_request(request_dict: dict[int, str], session: Session) -> int | None:
    """
    Returns id after successful insertion or None if insertion fails
    """
    rev_req_base = ReversalRequestBase(
        **get_message_base(request_dict, MessageBaseType.REV_REQ_BASE)
    )
    rev_req_base.pan = mask_pan(rev_req_base.pan)

    # Read field 90, populate the database and retrieve the ode_id
    ode_base = get_ode_base(request_dict[90])
    ode = OriginalDataElements.model_validate(ode_base)
    session.add(ode)
    session.commit()
    session.refresh(ode)

    if not ode.id:
        # Here, ode wasn't inserted successfully but it's id is necessary
        # TODO: Remove later
        print("ode insertion failed")
        return None

    ode_id = ode.id

    # find fin_req_id from the financial request table using de 90 stan,
    # "my" terminal_id and de 90 transmitted at since they're all echoed from the
    # financial request
    statement = select(FinancialRequest).where(
        FinancialRequest.stan == ode.stan
    ).where(
        FinancialRequest.transmitted_at == ode.transmitted_at
    ).where(
        FinancialRequest.terminal_id == rev_req_base.terminal_id
    )

    results = session.exec(statement).all()
    related_fin_req_id = results[0].id if results else None

    # plug it all in
    rev_req = ReversalRequest(
        **rev_req_base.model_dump(),
        raw_json=get_raw_json(request_dict),
        ode_id=ode_id,
        original_fin_req_id=related_fin_req_id
    )

    session.add(rev_req)
    session.commit()
    session.refresh(rev_req)
    return rev_req.id if rev_req.id else None

