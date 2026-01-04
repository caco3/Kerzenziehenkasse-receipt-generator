# Receipt Generator

This is the receipt generator for the Kerzenziehen.
It is able to generate the Swiss QR bill (svg file), Opendocument receipt (odt file) and PDF receipt (pdf file) or alternatively directly send it to the printer

## Project Structure

```
.
├── app/
│   └── main.py          # Flask application
├── requirements.txt     # Python dependencies
├── Dockerfile           # Docker configuration
├── docker-compose.yml   # Container orchestration
├── templates/
│   └── receipt.odt      # Receipt template
└── README.md            # This file
```

## Quick Start

```bash
docker compose up --build
```

## Endpoints

- `GET /` - Swagger API documentation
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
- `payment_type` (required) - Payment type: "bar", "Twint", or "EZS" (string)
- `output_type` (required) - Output type: "svg", "odt", "pdf" or "print" (string)

```

#### Response:
- **SVG**: Returns SVG file
- **ODT**: Returns ODT file
- **PDF**: Returns PDF file
- **Print**: Returns JSON with print job status:
```json
{
  "status": "printed",
  "job_id": "12345",
  "printer": "printer_queue_name"
}
```

#### Examples:

**Generate PDF:**
```bash
curl -X POST 'http://localhost:5000/api/generate-receipt' \
  -H 'Content-Type: application/json' \
  -d '{
    "value": 56.70,
    "booking_id": 1234,
    "teacher": "Frau Meier",
    "class": "Oberstufe Usterwest 3A",
    "payment_type": "bar",
    "output_type": "pdf"
  }' --output my-receipt.pdf
```

**Print Receipt:**
```bash
curl -X POST 'http://localhost:5000/api/generate-receipt' \
  -H 'Content-Type: application/json' \
  -d '{
    "value": 56.70,
    "booking_id": 1234,
    "teacher": "Frau Meier",
    "class": "Oberstufe Usterwest 3A",
    "payment_type": "EZS",
    "output_type": "print",
    "cups_queue_name": "printer_queue_name"
  }'
```

### 2. Check Printer Status

**GET** `/api/printer-status`

Get status and information about all available printers.

#### Response:
```json
{
  "printers": [
    {
      "name": "printer_queue_name",
      "device_uri": "hp:/usb/HP_LaserJet_Professional_P_1102w?serial=...",
      "status": "enabled|disabled|unknown",
      "ip_address": "192.168.1.100",  // null for local printers
      "type": "network|local",
      "description": "HP LaserJet Professional P 1102w"
    }
  ],
  "total_count": 1
}
```

#### Example:
```bash
curl -X GET 'http://localhost:5000/api/printer-status'
```

## Payment Types

- **bar**: Cash payment
- **Twint**: Twint payment
- **EZS**: Einzahlungsschein (QR bill)

## Output Types

- **svg**: QR bill as SVG image
- **odt**: OpenDocument Text template
- **pdf**: PDF document
- **print**: Send directly to printer

## Printer Configuration

To get a list of available printer queues:
```bash
lpstat -v
```

The label after "Gerät für" is the queue name to use for `cups_queue_name`.

## Access

The service is available at `http://localhost:5000`

## Stop

```bash
docker compose down
```
