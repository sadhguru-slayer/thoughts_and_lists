from pydantic import BaseModel

class ThoughtBase(BaseModel):
    id:int
    title:str
    content:str

class ThoughtCreate(BaseModel):
    title:str
    content:str