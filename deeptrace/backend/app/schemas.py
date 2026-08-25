from pydantic import BaseModel


class LoginIn(BaseModel):
    username: str
    password: str


class CaseIn(BaseModel):
    title: str
    offence_type: str = "digital_arrest"
    fir_number: str = ""
    station: str = "Cyber Cell, Chandigarh"
    priority: str = "P2"
    summary: str = ""


class BriefingIn(BaseModel):
    use_grok: bool = True
