from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import os
from datetime import date

from .db import get_conn
from .models import Device, Assignment, Person, Device_Type, Location
from .mqtt_integration import start_mqtt_listener

app = FastAPI(title="Inventar App", version="0.1.0")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


@app.on_event("startup")
def startup_event():
    start_mqtt_listener()


# ========== STARTSEITE ==========
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "Inventar App"}
    )


# ========== GERÄTE VERWALTEN ==========
@app.get("/devices", response_class=HTMLResponse)
def devices_page(request: Request):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT d.serial_number, dt.device_name, l.location_name, d.note
            FROM Device d
            JOIN Device_Type dt ON d.device_type_id = dt.type_id
            JOIN Location l ON d.location_id = l.location_id
            ORDER BY d.serial_number
        """)
        devices = list(cur.fetchall())

        # Für Dropdown-Listen
        cur.execute("SELECT type_id, device_name FROM Device_Type ORDER BY device_name")
        device_types = list(cur.fetchall())
        
        cur.execute("SELECT location_id, location_name FROM Location ORDER BY location_name")
        locations = list(cur.fetchall())

    return templates.TemplateResponse(
        "devices.html",
        {
            "request": request,
            "title": "Geräte verwalten",
            "devices": devices,
            "device_types": device_types,
            "locations": locations
        }
    )


@app.post("/add_device")
def add_device(
    device_nr: int = Form(...),
    device_type_id: int = Form(...),
    location_id: int = Form(...),
    note: str = Form(""),
    return_to: str = Form("/devices")
):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO Device (serial_number, device_type_id, location_id, note)
            VALUES (%s, %s, %s, %s)
        """, (device_nr, device_type_id, location_id, note))
    
    return RedirectResponse(return_to, status_code=303)


# ========== AUSLEIH-VERWALTUNG ==========
@app.get("/assignments", response_class=HTMLResponse)
def assignments_page(request: Request):
    with get_conn() as conn, conn.cursor() as cur:
        # Alle aktuellen Ausleihvorgänge
        cur.execute("""
            SELECT 
                a.device_id,
                d.serial_number,
                dt.device_name,
                a.person_id,
                p.person_name,
                a.issued_at,
                a.returned_at
            FROM Assignment a
            JOIN Device d ON a.device_id = d.serial_number
            JOIN Device_Type dt ON d.device_type_id = dt.type_id
            JOIN Person p ON a.person_id = p.personal_nr
            ORDER BY a.issued_at DESC
        """)
        assignments = list(cur.fetchall())

        # Für Dropdowns
        cur.execute("SELECT serial_number FROM Device ORDER BY serial_number")
        devices = list(cur.fetchall())
        
        cur.execute("SELECT personal_nr, person_name FROM Person ORDER BY person_name")
        persons = list(cur.fetchall())

    return templates.TemplateResponse(
        "assignments.html",
        {
            "request": request,
            "title": "Ausleihverwaltung",
            "assignments": assignments,
            "devices": devices,
            "persons": persons
        }
    )


@app.post("/device_issue")
def device_issue(
    device_nr: int = Form(...),
    personal_nr: int = Form(...),
    issued_at: date = Form(...),
    return_to: str = Form("/assignments")
):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO Assignment (device_id, person_id, issued_at, returned_at)
            VALUES (%s, %s, %s, NULL)
        """, (device_nr, personal_nr, issued_at))
    
    return RedirectResponse(return_to, status_code=303)


@app.post("/device_return")
def device_return(
    device_nr: int = Form(...),
    returned_at: date = Form(...),
    return_to: str = Form("/assignments")
):
    with get_conn() as conn, conn.cursor() as cur:
        # Update der neuesten offenen Ausleihe für dieses Gerät
        cur.execute("""
            UPDATE Assignment
            SET returned_at = %s
            WHERE device_id = %s 
            AND returned_at IS NULL
            AND issued_at = (
                SELECT MAX(issued_at) 
                FROM Assignment 
                WHERE device_id = %s AND returned_at IS NULL
            )
        """, (returned_at, device_nr, device_nr))

    return RedirectResponse(return_to, status_code=303)


# ========== HEALTH CHECK ==========
@app.get("/health")
def health():
    return {"status": "ok"}