# Python Webserver Docker Container

A simple Python webserver running in a Docker container using Flask.

## Project Structure

```
.
├── app/
│   └── main.py          # Flask application
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker configuration
├── docker-compose.yml  # Container orchestration
└── README.md           # This file
```

## Quick Start

```bash
docker compose up --build
```

## Endpoints

- `GET /` - Swagger API documentation
- `GET /health` - Health check endpoint
- `POST /api/generate-receipt` - Generate receipt as SVG image

### API Documentation

Interactive Swagger documentation is available at `http://localhost:5000/`

### Receipt Generation

Send a POST request to `/api/generate-receipt` with JSON data:

**Fields:**
- `value` (optional) - Payment amount (default: "56.70")
- `booking_id` (optional) - Reference/additional information (default: "Kerzenziehen 1234")
- `teacher` (optional) - Teacher name (default: "")
- `class` (optional) - Class name (default: "")
- `payment_type` (optional) - Payment type: "bar", "Twint", or "Einzahlungsschein" (default: "bar")

**Example request:**
```bash
curl -X 'POST' 'http://localhost:5000/api/generate-receipt' -H 'accept: application/json' -H 'Content-Type: application/json' -d '{
  "value": "56.70",
  "booking_id": "1234",
  "teacher": "Frau Meier",
  "class": "Oberstufe Usterwest 3A",
  "payment_type": "bar"
}' --output receipt.svg
```

The receipt will be generated with the predefined account information for Viva Kirche Schweiz.

## Access

The webserver will be available at `http://localhost:5000`

## Stop

```bash
docker compose down
```
