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
- `POST /api/generate-receipt` - Generate receipt based on output type

### API Documentation

Interactive Swagger documentation is available at `http://localhost:5000/`

### Receipt Generation

Send a POST request to `/api/generate-receipt` with JSON data:

**Required Fields:**
- `value` (required) - Payment amount (float)
- `booking_id` (required) - Reference/additional information (integer)
- `teacher` (required) - Teacher name (string)
- `class` (required) - Class name (string)
- `payment_type` (required) - Payment type: "bar", "Twint", or "Einzahlungsschein" (string)
- `output_type` (required) - Output type: "svg", "odt", or "pdf" (string)

**Output Types:**
- `svg` - Generate QR Bill as SVG image ✅
- `odt` - Generate receipt as ODT document with QR bill and filled placeholders ✅
- `pdf` - Generate receipt as PDF document (not implemented yet)

**Example request:**
```bash
# Select expected output type
OUTPUT_TYPE="pdf"
#OUTPUT_TYPE="odt"
#OUTPUT_TYPE="svg"

# Generate
curl -X 'POST' 'http://localhost:5000/api/generate-receipt' -H 'accept: application/json' -H 'Content-Type: application/json' -d '{
  "value": 56.70,
  "booking_id": 1234,
  "teacher": "Frau Meier",
  "class": "Oberstufe Usterwest 3A",
  "payment_type": "bar",
  "output_type": "$OUTPUT_TYPE"
}' --output my-receipt.svg
```

The receipt will be generated with the predefined account information for Viva Kirche Schweiz.

## Access

The webserver will be available at `http://localhost:5000`

## Stop

```bash
docker compose down
```
