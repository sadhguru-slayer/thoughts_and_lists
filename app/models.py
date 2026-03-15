from sqlalchemy import Column, Integer, String
from app.database import Base

class Thought(Base):
    __tablename__ = "thoughts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    content = Column(String, nullable=False)