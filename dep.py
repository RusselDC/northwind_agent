from config import settings
from sqlmodel import create_engine, Session as DbSessionType
from fastapi import Depends
from typing import Annotated


db_engine = create_engine(settings.DATABASE_URL, echo=True)
def get_session():
    with DbSessionType(db_engine) as session:
        yield session
        
        
Session =  Annotated[DbSessionType, Depends(get_session)]