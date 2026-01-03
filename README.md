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

**Output Types:**
- `svg` - Generate QR Bill as SVG image
- `odt` - Generate receipt as ODT document with QR bill and filled placeholders
- `pdf` - Generate receipt as PDF document with QR bill and filled placeholders
- `print` - Generate receipt as PDF document with QR bill and filled placeholders and print it

**Example requests to generate the QR bill (svg), the receipt document (odt) or the PDF out of it (pdf):**
```bash
OUTPUT_TYPE="pdf"
#OUTPUT_TYPE="odt"
#OUTPUT_TYPE="svg"

curl -X 'POST' 'http://localhost:5000/api/generate-receipt' -H 'accept: application/json' -H 'Content-Type: application/json' -d "{
  \"value\": 56.70,
  \"booking_id\": 1234,
  \"teacher\": \"Frau Meier\",
  \"class\": \"Oberstufe Usterwest 3A\",
  \"payment_type\": \"bar\",
  \"output_type\": \"$OUTPUT_TYPE\",
  \"cups_queue_name\": \"$PRINTER_QUEUE_NAME\"
}" --output my-receipt.$OUTPUT_TYPE
```

**Example request to generate and print it (print):**
```bash
curl -X POST 'http://localhost:5000/api/generate-receipt' \
  -H 'Content-Type: application/json' \
  -d '{
    "value": 56.70,
    "booking_id": 1234,
    "teacher": "Frau Meier",
    "class": "Oberstufe Usterwest 3A",
    "payment_type": "EZS",
    "output_type": "print"
  }'
```

This will use the default printer configured in the host system.

To select another printer, its CUPS queue name must be specified:
`cups_queue_name="<printer_queue_name>"`.

To get the CUPS queue name of a printer, run:
`lpstat -v | grep usb | awk -F ' ' '{print $3}' | sed "s/://"` # The label after "Gerät für" is the queue name.

## Access

The service is available at `http://localhost:5000`

## Stop

```bash
docker compose down
```
