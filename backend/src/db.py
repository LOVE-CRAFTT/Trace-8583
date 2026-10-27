"""
Provides function to create the database and tables
Provides a managed session object type
"""
import os
from pathlib import Path
from functools import cache
from typing import Annotated
from dotenv import load_dotenv
from fastapi import Depends
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import MetaData, Table, text

STATUS_VIEW_SQL = Path(__file__).parent/"database"/"status_view.sql"
view_metadata = MetaData()

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

def get_session():
    """Yield a session object per database operation"""
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]


def create_db_and_tables():
    """
    Creates the database and the tables
    then (re)create the status view
    """
    SQLModel.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text(STATUS_VIEW_SQL.read_text()))

@cache
def get_status_view() -> Table:
    """ Returns the dynamically generated view data from the database"""
    return Table("transaction_status", view_metadata, autoload_with=engine)

if __name__ == "__main__":
    print(DATABASE_URL)
