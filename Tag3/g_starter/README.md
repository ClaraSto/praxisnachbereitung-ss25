# Grades Starter

Kleine Demo-App für die Domäne **Student / Module / Grade** mit:

- FastAPI
- PostgreSQL
- MQTT (Eclipse Mosquitto)
- Einfacher HTML-Oberfläche (Jinja + htmx)
- CSV-Export `grades.csv`

## Start

Voraussetzungen:

- Docker + Docker Compose

Dann im Projektordner:

```bash
docker compose up -d --build
```

Services:

- API: http://localhost:8000
- Postgres: localhost:5432
- MQTT: localhost:1883 (TCP), localhost:9001 (WebSockets)

## Wichtige Endpoints

- `GET /` – Startseite mit Links
- `GET /grades` – UI zum Erfassen und Anzeigen von Noten
- `POST /students` – neuen Studenten anlegen (per Formular)
- `POST /modules` – neues Modul anlegen (per Formular)
- `POST /grades/htmx` – neue Note anlegen (Formular via htmx)
- `GET /grades.csv` – CSV aller Noten inkl. Student- und Modul-Infos
- `GET /health` – Health-Check
- `GET /docs` – OpenAPI-Dokumentation

## Datenmodell

Tabellen:

- `student (student_id, matrikel, name, programme, semester)`
- `module (module_id, name)`
- `grade (grade_id, student_id, module_id, grade_value, graded_at)`

Beim ersten Start werden in `001_schema.sql` einige Testdaten angelegt.

## MQTT

Die API abonniert beim Start das Topic:

- `grades/new`

Erwartetes Payload-Format (JSON):

```json
{
  "student_id": 1,
  "module_id": 2,
  "grade_value": "1,7"
}
```

Beispiel-Publish (mit `mosquitto_pub`, wenn auf dem Host installiert):

```bash
mosquitto_pub -h localhost -p 1883 -t "grades/new" -m '{"student_id":1,"module_id":2,"grade_value":"1,0"}'
```

Nach erfolgreicher Nachricht sollte auf `/grades` die neue Note erscheinen und im CSV-Export (`/grades.csv`) sichtbar sein.
