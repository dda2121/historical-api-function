from uuid import uuid4

from pydantic import BaseModel
from iot_hub_database import Base
from sqlalchemy import Column, UUID, String


class QueryRequest(BaseModel):
    deviceName: str
    dateFrom: str
    dateTo: str

class QueryResponse(BaseModel):
    body: str
    enqueuedTime: str


class HubDB(Base):
    __tablename__ = "iot_hub"
    __table_args__ = {'schema': 'smart_house'}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    name = Column(String, index=True)
    user_id = Column(UUID(as_uuid=True))