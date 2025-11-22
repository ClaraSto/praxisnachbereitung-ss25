from datetime import date
from pydantic import BaseModel

class Device_Type(BaseModel):
    type_id: int
    device_name: str

class Location(BaseModel):
    location_id: int
    location_name: str

class Person(BaseModel):
    personal_nr: int
    person_name: str

class Device(BaseModel):
    serial_number: int
    device_type_id: int
    location_id: int
    note: str | None = None

class Assignment(BaseModel):
    device_id: int
    person_id: int
    issued_at: date
    returned_at: date | None = None