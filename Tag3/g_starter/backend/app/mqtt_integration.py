import os
import json
import threading
import time
from datetime import datetime
import paho.mqtt.client as mqtt
from .db import get_conn

MQTT_HOST = os.getenv("MQTT_HOST", "mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC_DEVICE = os.getenv("MQTT_DEVICE_TOPIC", "device/new")
MQTT_TOPIC_ISSUE = os.getenv("MQTT_ISSUE_TOPIC", "assignment/issue")
MQTT_TOPIC_RETURN = os.getenv("MQTT_RETURN_TOPIC", "assignment/return")

def _parse_date(date_str: str):
    """Konvertiert Datum im Format DD.MM.YYYY zu einem date-Objekt."""
    try:
        return datetime.strptime(date_str, "%d.%m.%Y").date()
    except Exception:
        return None

def _handle_device_new(data: dict):
    """Verarbeitet device/new Topic"""
    try:
        device_id = int(data["device_id"])
        device_name = str(data["device_name"])
        location_id = int(data["location_id"])
        note = data.get("note", "")
        
        with get_conn() as conn, conn.cursor() as cur:
            # Prüfe ob Gerät bereits existiert
            cur.execute("SELECT COUNT(*) FROM Device WHERE serial_number = %s", (device_id,))
            if cur.fetchone()[0] > 0:
                print(f"[MQTT] Gerät {device_id} existiert bereits, wird übersprungen")
                return
            
            # Hole location_id anhand des Namens
            cur.execute("SELECT id FROM Location WHERE name = %s", (location_id,))
            location_result = cur.fetchone()
            if not location_result:
                print(f"[MQTT] Location '{location_id}' nicht gefunden")
                return
            location_id = location_result[0]
            
            # Hole device_type_id (z.B. anhand des device_name oder verwende Standard)
            # Hier musst du entscheiden, wie device_type ermittelt wird
            # Beispiel: Verwende einen Standard-Typ oder parse den Namen
            cur.execute("SELECT id FROM DeviceType LIMIT 1")
            device_type_result = cur.fetchone()
            if not device_type_result:
                print(f"[MQTT] Kein DeviceType gefunden")
                return
            device_name = device_type_result[0]
            
            cur.execute("""
                INSERT INTO Device (serial_number, device_name, location_id, note)
                VALUES (%s, %s, %s, %s)
            """, (device_id, device_name, location_id, note))
            
        print(f"[MQTT] Neues Gerät angelegt: device_id={device_id}, location={location_name}")
    except Exception as exc:
        print("[MQTT] Fehler bei device/new:", exc)

def _handle_assignment_issue(data: dict):
    """Verarbeitet assignment/issue Topic"""
    try:
        device_id = int(data["device_id"])
        personal_id = int(data["personal_id"])
        personal_name = str(data["personal_name"])
        issued_at_str = str(data["issued_at"])
        issued_at = _parse_date(issued_at_str)
        
        if not issued_at:
            print(f"[MQTT] Ungültiges Datum: {issued_at_str}")
            return
        
        with get_conn() as conn, conn.cursor() as cur:
            # Prüfe ob Gerät bereits ausgeliehen ist
            cur.execute("""
                SELECT COUNT(*) FROM Assignment 
                WHERE device_id = %s AND returned_at IS NULL
            """, (device_id,))
            
            if cur.fetchone()[0] > 0:
                print(f"[MQTT] Gerät {device_id} ist bereits ausgeliehen")
                return
            
            # Prüfe ob Person existiert
            cur.execute("SELECT COUNT(*) FROM Person WHERE id = %s", (personal_id,))
            if cur.fetchone()[0] == 0:
                print(f"[MQTT] Person {personal_id} nicht gefunden")
                return
            
            cur.execute("""
                INSERT INTO Assignment (device_id, person_id, issued_at, returned_at)
                VALUES (%s, %s, %s, NULL)
            """, (device_id, personal_id, issued_at))
            
        print(f"[MQTT] Neue Ausleihe: device_id={device_id}, person_id={personal_id}, issued_at={issued_at}")
    except Exception as exc:
        print("[MQTT] Fehler bei assignment/issue:", exc)

def _handle_assignment_return(data: dict):
    """Verarbeitet assignment/return Topic"""
    try:
        device_id = int(data["device_id"])
        returned_at_str = str(data["returned_at"])
        returned_at = _parse_date(returned_at_str)
        
        if not returned_at:
            print(f"[MQTT] Ungültiges Datum: {returned_at_str}")
            return
        
        with get_conn() as conn, conn.cursor() as cur:
            # Hole issued_at der offenen Ausleihe
            cur.execute("""
                SELECT issued_at FROM Assignment
                WHERE device_id = %s AND returned_at IS NULL
                ORDER BY issued_at DESC LIMIT 1
            """, (device_id,))
            
            result = cur.fetchone()
            if not result:
                print(f"[MQTT] Keine offene Ausleihe für Gerät {device_id} gefunden")
                return
            
            issued_at = result[0]
            
            # Validierung: returned_at muss nach issued_at sein
            if returned_at < issued_at:
                print(f"[MQTT] Rückgabedatum ({returned_at}) liegt vor Ausgabedatum ({issued_at})")
                return
            
            cur.execute("""
                UPDATE Assignment
                SET returned_at = %s
                WHERE device_id = %s AND returned_at IS NULL AND issued_at = %s
            """, (returned_at, device_id, issued_at))
            
        print(f"[MQTT] Rückgabe registriert: device_id={device_id}, returned_at={returned_at}")
    except Exception as exc:
        print("[MQTT] Fehler bei assignment/return:", exc)

def _on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
    """Wird aufgerufen, wenn eine Nachricht auf einem abonnierten Topic eingeht."""
    try:
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload)
        topic = msg.topic
        
        if topic == MQTT_TOPIC_DEVICE:
            _handle_device_new(data)
        elif topic == MQTT_TOPIC_ISSUE:
            _handle_assignment_issue(data)
        elif topic == MQTT_TOPIC_RETURN:
            _handle_assignment_return(data)
        else:
            print(f"[MQTT] Unbekanntes Topic: {topic}")
            
    except Exception as exc:
        print("[MQTT] Ungültiges Payload, wird ignoriert:", exc)

def _mqtt_loop():
    """Verbindet sich mit dem Broker, abonniert die Topics und läuft in einer Endlosschleife."""
    while True:
        try:
            client = mqtt.Client()
            client.on_message = _on_message
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
            
            # Abonniere alle drei Topics
            client.subscribe(MQTT_TOPIC_DEVICE, qos=0)
            client.subscribe(MQTT_TOPIC_ISSUE, qos=0)
            client.subscribe(MQTT_TOPIC_RETURN, qos=0)
            
            print(f"[MQTT] Verbunden mit {MQTT_HOST}:{MQTT_PORT}")
            print(f"[MQTT] Topics abonniert: {MQTT_TOPIC_DEVICE}, {MQTT_TOPIC_ISSUE}, {MQTT_TOPIC_RETURN}")
            
            client.loop_forever()
        except Exception as exc:
            print("[MQTT] Verbindungsfehler, neuer Versuch in 5s:", exc)
            time.sleep(5)

def start_mqtt_listener():
    """Startet den MQTT-Listener in einem Hintergrundthread."""
    t = threading.Thread(target=_mqtt_loop, daemon=True)
    t.start()