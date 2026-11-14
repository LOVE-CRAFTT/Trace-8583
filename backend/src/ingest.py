"""
Module containing functions for processing ingested iso_8583 messages
"""

from sqlmodel import select, Session
from sqlalchemy.exc import IntegrityError
from .utils import (mask_pan,
                    get_raw_json,
                    get_message_base,
                    MessageBaseType,
                    get_ode
                    )
from .models import (FinancialRequest,
                     FinancialResponse,
                     ReversalRequest,
                     ReversalResponse
                     )
from .models import (FinancialRequestBase,
                     FinancialResponseBase,
                     ReversalRequestBase,
                     ReversalResponseBase)
from .db import engine
from .iso_8583.iso8583 import iso_8583_to_json as iso_8583


def process(hex_string: str):
    """
    Takes a single hex string and based on the MTI, delegate to appropriate
    database insertion function.
    """
    result = None
    message_dict = iso_8583(hex_string)
    if message_dict:
        mti = message_dict[0]
        try:
            with Session(engine) as session:
                match mti:
                    case "0200":
                        result = insert_financial_request(message_dict, session)
                    case "0210":
                        result = insert_financial_response(message_dict, session)
                    case "0400":
                        result = insert_reversal_request(message_dict, session)
                    case "0410":
                        result = insert_reversal_response(message_dict, session)
                    case _:
                        result = message_dict
        except IntegrityError as e:
            # 23505 identifies duplicate messages: skip silently
            if getattr(e.orig, "sqlstate", None) != "23505":
                print(e.statement, e)

    return result


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
    return fin_req.id


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
    result = session.exec(statement).one_or_none()

    # There should be exactly one related fin_req
    # but still insert but related request id would be null
    related_fin_req = result if result else None
    fin_resp =  FinancialResponse(
        **fin_resp_base.model_dump(),
        raw_json=get_raw_json(response_dict),
        request_id=related_fin_req.id if result else None
    )

    session.add(fin_resp)
    session.commit()
    session.refresh(fin_resp)
    return fin_resp.id


def insert_reversal_request(request_dict: dict[int, str], session: Session) -> int | None:
    """
    Returns id after successful insertion or None if insertion fails
    """
    rev_req_base = ReversalRequestBase(
        **get_message_base(request_dict, MessageBaseType.REV_REQ_BASE)
    )
    rev_req_base.pan = mask_pan(rev_req_base.pan)

    # Read field 90, populate the database and retrieve the ode_id
    original_de = request_dict.get(90)
    if not original_de:
        return None

    ode = get_ode(original_de, session)

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

    result = session.exec(statement).one_or_none()
    related_fin_req_id = result.id if result else None

    # plug it all in
    rev_req = ReversalRequest(
        **rev_req_base.model_dump(),
        raw_json=get_raw_json(request_dict),
        ode_id=ode.id,
        original_fin_req_id=related_fin_req_id
    )

    session.add(rev_req)
    session.commit()
    session.refresh(rev_req)
    return rev_req.id


def insert_reversal_response(response_dict: dict[int, str], session: Session) -> int | None:
    """
    Returns id after successful insertion or None if insertion fails
    """
    rev_resp_base = ReversalResponseBase(
        **get_message_base(response_dict, MessageBaseType.REV_RESP_BASE)
    )
    rev_resp_base.pan = mask_pan(rev_resp_base.pan)

    # Read field 90, populate the database and retrieve the ode_id
    original_de = response_dict.get(90)
    if not original_de:
        return None

    ode = get_ode(original_de, session)

    # try to get the reversal request using the unique values which are echoed
    statement = select(ReversalRequest).where(
    ReversalRequest.stan == rev_resp_base.stan
    ).where(
        ReversalRequest.terminal_id == rev_resp_base.terminal_id
    ).where(
        ReversalRequest.loc_txn_date == rev_resp_base.loc_txn_date
    )
    result = session.exec(statement).one_or_none()
    related_reversal_req_id = result.id if result else None

    # then create the reversal response and commit
    # plug it all in
    rev_resp = ReversalResponse(
        **rev_resp_base.model_dump(),
        raw_json=get_raw_json(response_dict),
        ode_id=ode.id,
        reversal_req_id=related_reversal_req_id
    )

    session.add(rev_resp)
    session.commit()
    session.refresh(rev_resp)
    return rev_resp.id
