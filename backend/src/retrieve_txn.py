"""
Module containing funtions to retrive transaction(s) from the database
"""

from sqlmodel import select, Session
from sqlalchemy import select as sa_select
from .db import get_status_view, engine
from .models import FinancialRequest


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
