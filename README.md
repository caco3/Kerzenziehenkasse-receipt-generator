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
- `POST /api/generate-qr` - Generate Swiss QR Bill as SVG image

### API Documentation

Interactive Swagger documentation is available at `http://localhost:5000/`

### QR Code Generation

Send a POST request to `/api/generate-qr` with JSON data:

**Fields:**
- `value` (optional) - Payment amount (default: "0.00")
- `additional_information` (optional) - Reference/additional information

**Example request:**
```bash
curl -X 'POST' 'http://localhost:5000/api/generate-qr' -H 'accept: application/json' -H 'Content-Type: application/json' -d '{"value": "56.70","additional_information": "Kerzenziehen 1234"}' --output qr-bill.svg
```

The QR bill will be generated with the predefined account information for Viva Kirche Schweiz.

## Access

The webserver will be available at `http://localhost:5000`

## Stop

```bash
docker compose down
```
