"""
Define all SQLModel models

Base classes (no table=True) hold the message fields and validate input.
Table classes inherit a base, add database-only columns, and map to tables
"""
from datetime import UTC, datetime

from sqlmodel import SQLModel, Field, UniqueConstraint
from sqlmodel import BigInteger, DateTime, CHAR
from sqlalchemy.dialects.postgresql import JSONB

class MessageBase(SQLModel):
    """
    Fields shared by all response and request tables
    """

    pan:             str =         Field(max_length=19)
    processing_code: str =         Field(min_length=6, max_length=6, sa_type=CHAR(6))
    amount:          int =         Field(sa_type=BigInteger)
    transmitted_at:  str =         Field(min_length=10, max_length=10, sa_type=CHAR(10))
    stan:            str =         Field(min_length=6, max_length=6, sa_type=CHAR(6))
    loc_txn_time:    str =         Field(min_length=6, max_length=6, sa_type=CHAR(6))
    loc_txn_date:    str =         Field(min_length=4, max_length=4, sa_type=CHAR(4))
    rrn:             str | None =  Field(None, min_length=12, max_length=12, sa_type=CHAR(12))
    terminal_id:     str =         Field(min_length=8, max_length=8, sa_type=CHAR(8))
    merchant_id:     str =         Field(min_length=15, max_length=15, sa_type=CHAR(15))
    currency:        str =         Field(min_length=3, max_length=3, sa_type=CHAR(3))


class FinancialRequestBase(MessageBase):
    # pylint: disable=missing-class-docstring
    mcc:             str | None =  Field(None, min_length=4, max_length=4, sa_type=CHAR(4))
    pos_entry_mode:  str | None =  Field(None, min_length=3, max_length=3, sa_type=CHAR(3))
    pos_condition:   str | None =  Field(None, min_length=2, max_length=2, sa_type=CHAR(2))
    acquirer_id:     str | None =  Field(None, max_length=11)

class FinancialResponseBase(MessageBase):
    # pylint: disable=missing-class-docstring
    auth_id_resp:    str | None =  Field(min_length=6, max_length=6, sa_type=CHAR(6))
    resp_code:       str =         Field(min_length=2, max_length=2, sa_type=CHAR(2))

class ReversalRequestBase(MessageBase):
    # pylint: disable=missing-class-docstring
    mcc:             str | None =  Field(None, min_length=4, max_length=4, sa_type=CHAR(4))
    acquirer_id:     str | None =  Field(None, max_length=11)

class ReversalResponseBase(MessageBase):
    # pylint: disable=missing-class-docstring
    mcc:             str | None =  Field(None, min_length=4, max_length=4, sa_type=CHAR(4))
    acquirer_id:     str | None =  Field(None, max_length=11)
    resp_code:       str =         Field(min_length=2, max_length=2, sa_type=CHAR(2))

class OriginalDataElementsBase(SQLModel):
    # pylint: disable=missing-class-docstring
    mti:             str =         Field(min_length=4, max_length=4, sa_type=CHAR(4))
    stan:            str =         Field(min_length=6, max_length=6, sa_type=CHAR(6))
    transmitted_at:  str =         Field(min_length=10, max_length=10, sa_type=CHAR(10))
    acquirer_id:     str | None =  Field(None, max_length=11)
    forwarder_id:    str | None =  Field(None, max_length=11)

class MessageRecord(SQLModel):
    """
    Database-only columns shared by all 4 tables
    """
    id:              int | None =     Field(None, sa_type=BigInteger, primary_key=True)
    raw_json:        dict =           Field(sa_type=JSONB)
    created_at:      datetime =       Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True)
    )

class OriginalDataElements(OriginalDataElementsBase, table=True):
    """
    Original Data Elements Table Model
    """
    __tablename__ = "original_data_elements"
    __table_args__ = (UniqueConstraint("mti", "transmitted_at", "stan"),)

    id:              int | None =     Field(None, sa_type=BigInteger, primary_key=True)

class FinancialRequest(FinancialRequestBase, MessageRecord, table=True):
    """
    Financial Request Table Model
    """
    __tablename__ = "financial_request"
    __table_args__ = (UniqueConstraint("stan", "terminal_id","loc_txn_date"),)

class FinancialResponse(FinancialResponseBase, MessageRecord, table=True):
    """
    Financial Response Table Model
    """
    __tablename__ = "financial_response"
    __table_args__ = (UniqueConstraint("stan", "terminal_id","loc_txn_date"),)

    request_id:      int | None=      Field(
        None, foreign_key="financial_request.id", sa_type=BigInteger
    )

class ReversalRequest(ReversalRequestBase, MessageRecord, table=True):
    """
    Reversal Request Table Model
    """
    __tablename__ = "reversal_request"
    __table_args__ = (UniqueConstraint("stan", "terminal_id","loc_txn_date"),)

    ode_id:                 int =            Field(
        foreign_key="original_data_elements.id",
        sa_type=BigInteger
    )
    original_fin_req_id:    int | None =     Field(
        None,
        foreign_key="financial_request.id",
        sa_type=BigInteger
    )

class ReversalResponse(ReversalResponseBase, MessageRecord, table=True):
    """
    Reversal Response Table Model
    """
    __tablename__ = "reversal_response"
    __table_args__ = (UniqueConstraint("stan", "terminal_id","loc_txn_date"),)

    ode_id:                 int =            Field(
        foreign_key="original_data_elements.id",
        sa_type=BigInteger
    )
    reversal_req_id:        int | None =     Field(
        None,
        foreign_key="reversal_request.id",
        sa_type=BigInteger
    )

if __name__ == "__main__":
    # Generate the SQL by default
    from sqlalchemy import create_mock_engine

    def dump(sql, *_args, **kwargs):
        # pylint: disable=unused-argument
        # pylint: disable=missing-function-docstring
        print(sql.compile(dialect=engine.dialect))

    engine = create_mock_engine("postgresql://", dump)
    SQLModel.metadata.create_all(engine, checkfirst=False)
