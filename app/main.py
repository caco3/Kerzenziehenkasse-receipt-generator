from flask import Flask, jsonify, request, send_file
import io
import re
import zipfile
import tempfile
import os
import xml.etree.ElementTree as ET
from datetime import datetime
import subprocess
from flask_restx import Api, Resource, fields
from qrbill import QRBill

# Account data
iban = "CH05 0688 8016 1232 5000 7"
name = "Viva Kirche Schweiz"
street = "Kirche Neuwies Uster"
postal_code = 4126
city = "Bettingen"

def convert_odt_to_pdf(odt_buffer):
    """Convert ODT buffer to PDF using LibreOffice"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Save ODT buffer to temporary file
        odt_path = os.path.join(temp_dir, 'receipt.odt')
        with open(odt_path, 'wb') as f:
            f.write(odt_buffer.getvalue())
        
        # Convert to PDF using LibreOffice
        try:
            result = subprocess.run([
                'libreoffice',
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', temp_dir,
                odt_path
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise Exception(f"LibreOffice conversion failed: {result.stderr}")
            
            # Read the generated PDF
            pdf_path = os.path.join(temp_dir, 'receipt.pdf')
            if os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as f:
                    pdf_buffer = io.BytesIO(f.read())
                pdf_buffer.seek(0)
                return pdf_buffer
            else:
                raise Exception("PDF file was not generated")
                
        except subprocess.TimeoutExpired:
            raise Exception("LibreOffice conversion timed out")
        except Exception as e:
            raise Exception(f"Error converting ODT to PDF: {str(e)}")

def print_pdf_via_cups(pdf_buffer, cups_queue_name=None):
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(pdf_buffer.getvalue())
        tmp_path = tmp.name

    try:
        cmd = ['lp']
        if cups_queue_name:
            cmd.extend(['-d', cups_queue_name])
        cmd.append(tmp_path)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise Exception(f"CUPS print failed: {result.stderr.strip() or result.stdout.strip()}")

        job_id = (result.stdout or '').strip()
        return job_id
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

def get_cups_printers():
    """Query CUPS for configured printers via lpstat.

    Returns a list of dicts with name, status, description, type and
    ip_address - the shape the Kassen-Software printer dialog expects.
    """
    try:
        p_result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True, timeout=10)
        v_result = subprocess.run(['lpstat', '-v'], capture_output=True, text=True, timeout=10)
    except FileNotFoundError:
        raise Exception("lpstat not available - CUPS client tools missing")
    if p_result.returncode != 0:
        raise Exception(f"lpstat failed: {p_result.stderr.strip()}")

    # Map queue name -> device URI (usb://, hp:/usb/, ipp://, dnssd://, ...)
    uris = {}
    for line in v_result.stdout.splitlines():
        m = re.match(r'device for (\S+):\s*(\S+)', line)
        if m:
            uris[m.group(1)] = m.group(2)

    printers = []
    for line in p_result.stdout.splitlines():
        m = re.match(r'printer (\S+)', line)
        if not m:
            continue
        name = m.group(1)
        uri = uris.get(name, '')
        if uri.startswith('usb:') or '/usb/' in uri:
            ptype = 'usb'
        elif re.match(r'(ipp|ipps|socket|lpd|dnssd|mdns|http|https)://', uri):
            ptype = 'network'
        else:
            ptype = 'other'
        ip_match = re.search(r'://([^/\s:]+)', uri)
        printers.append({
            'name': name,
            'status': 'disabled' if 'disabled' in line else 'enabled',
            'description': name,
            'type': ptype,
            'ip_address': ip_match.group(1) if ptype == 'network' and ip_match else ''
        })
    return printers

def generate_qr_bill_svg(booking_id, value):
    """Generate the Swiss QR-bill SVG for an invoice payment"""
    additional_info = "Kerzenziehen " + str(booking_id)
    bill = QRBill(
        account=iban,
        creditor={
            'name': name,
            'street': street,
            'pcode': str(postal_code),
            'city': city,
            'country': 'CH'
        },
        amount=str(value),
        currency='CHF',
        additional_information=additional_info,
        language='de'
    )
    svg_buffer = io.StringIO()
    bill.as_svg(svg_buffer)
    svg_data = svg_buffer.getvalue()
    svg_buffer.close()
    return svg_data

def process_odt_template(booking_id, teacher, class_name, value, payment_type):
    """Process ODT template by replacing placeholders and QR code"""
    # Get current date and time
    now = datetime.now()
    current_year = now.year
    current_time = now.strftime("%H:%M")
    current_date = now.strftime("%d.%m.%Y")

    # bill.odt is the invoice template (only for EZS/Rechnung);
    # receipt.odt covers cash (bar) and Twint payments.
    is_invoice = payment_type.lower() == 'ezs'
    odt_template_path = '/templates/bill.odt' if is_invoice else '/templates/receipt.odt'

    # Create temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract ODT template
        with zipfile.ZipFile(odt_template_path, 'r') as template_zip:
            template_zip.extractall(temp_dir)

        content_xml_path = os.path.join(temp_dir, 'content.xml')
        with open(content_xml_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if is_invoice:
            # Replace the picture embedded by the template's 'qr-bill' frame
            # with the generated slip. LibreOffice renames embedded pictures on
            # every save, so resolve the image path from the frame's xlink:href.
            frame_match = re.search(
                r'<draw:frame\b[^>]*draw:name="qr-bill"[^>]*>(.*?)</draw:frame>',
                content, re.S)
            if not frame_match:
                raise Exception("qr-bill frame not found in template")
            hrefs = re.findall(r'xlink:href="([^"]+)"', frame_match.group(1))
            image_href = next((h for h in hrefs if h.lower().endswith('.svg')),
                              hrefs[0] if hrefs else None)
            if not image_href:
                raise Exception("qr-bill frame contains no image")
            image_path = os.path.normpath(os.path.join(temp_dir, image_href))
            with open(image_path, 'w', encoding='utf-8') as f:
                f.write(generate_qr_bill_svg(booking_id, value))

        # Replace placeholders in content.xml
        
        # Replace all placeholders
        replacements = {
            '{year}': str(current_year),
            '{time}': current_time,
            '{date}': current_date,
            '{bookingId}': str(booking_id),
            '{class}': class_name,
            '{teacher}': teacher,
            '{priceTotal}': f"{value:.2f}"
        }
        
        for placeholder, replacement in replacements.items():
            content = content.replace(placeholder, replacement)

        # Fill named form text controls (LibreOffice may save the class/teacher
        # inputs as form:text fields; their displayed value is form:current-value)
        form_values = {
            'Schulklasse': class_name,
            'Leiter/In': teacher,
        }
        for field_name, field_value in form_values.items():
            def fill_field(match, value=field_value):
                tag = re.sub(r'\sform:(current-)?value="[^"]*"', '', match.group(0))
                return tag.replace('>', ' form:current-value="{0}" form:value="{0}">'.format(value), 1)
            content = re.sub(
                r'<form:text\b[^>]*form:name="' + re.escape(field_name) + r'"[^>]*>',
                fill_field, content, count=1)

        # Check the appropriate payment type checkbox
        if payment_type.lower() == 'bar':
            content = content.replace('<form:checkbox form:name="Bar"', '<form:checkbox form:name="Bar" form:current-state="checked"')
        elif payment_type.lower() == 'twint':
            content = content.replace('<form:checkbox form:name="Twint"', '<form:checkbox form:name="Twint" form:current-state="checked"')
        
        # Write updated content.xml
        with open(content_xml_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Create new ODT file in memory
        odt_buffer = io.BytesIO()
        with zipfile.ZipFile(odt_buffer, 'w', zipfile.ZIP_DEFLATED) as new_odt:
            # Add all files from temp directory
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, temp_dir)
                    new_odt.write(file_path, arc_path)
        
        odt_buffer.seek(0)
        return odt_buffer

app = Flask(__name__)
api = Api(app, version='1.0', title='Receipt Generator for the Kerzenziehen',
          description='Tool to generate the receipt and directly print it',
          doc='/', default='api', default_label='Receipt Generator API')


@app.after_request
def add_cors_headers(response):
    # The Kassen-Software page (port 80) calls this API cross-origin on :8087
    # with a JSON body, so the browser requires CORS headers.
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

# Model for receipt generation request
receipt_request_model = api.model('ReceiptRequest', {
    'value': fields.Float(required=True, description='Payment amount'),
    'booking_id': fields.Integer(required=True, description='Booking ID'),
    'teacher': fields.String(required=True, description='Teacher name'),
    'class': fields.String(required=True, description='Class name'),
    'payment_type': fields.String(required=True, description='Payment type: bar or Twint use receipt.odt, EZS (Rechnung) uses bill.odt'),
    'output_type': fields.String(required=True, description='Output type: svg, odt, pdf, print'),
    'cups_queue_name': fields.String(required=False, description='CUPS printer/queue name (optional, only needed for printing; falls back to CUPS default)')
})

@api.route('/api/generate-receipt')
class GenerateReceipt(Resource):
    @api.doc('generate_receipt')
    @api.expect(receipt_request_model)
    def post(self):
        """Generate receipt based on output type"""
        try:
            data = request.get_json()
            
            # Get all fields from request
            value = data.get('value')
            booking_id = data.get('booking_id')
            teacher = data.get('teacher')
            class_name = data.get('class')
            payment_type = data.get('payment_type')
            output_type = data.get('output_type')
            cups_queue_name = data.get('cups_queue_name')
            
            if output_type == 'svg':
                svg_data = generate_qr_bill_svg(booking_id, value)
                
                # Return as SVG file
                svg_bytes = io.BytesIO(svg_data.encode('utf-8'))
                svg_bytes.seek(0)
                return send_file(
                    svg_bytes,
                    mimetype='image/svg+xml',
                    as_attachment=False,
                    download_name='receipt.svg'
                )
                
            elif output_type == 'odt':
                # Generate ODT receipt
                odt_buffer = process_odt_template(booking_id, teacher, class_name, value, payment_type)
                return send_file(
                    odt_buffer,
                    mimetype='application/vnd.oasis.opendocument.text',
                    as_attachment=False,
                    download_name='receipt.odt'
                )
                
            elif output_type == 'pdf':
                # Generate PDF receipt by converting ODT
                odt_buffer = process_odt_template(booking_id, teacher, class_name, value, payment_type)
                pdf_buffer = convert_odt_to_pdf(odt_buffer)
                return send_file(
                    pdf_buffer,
                    mimetype='application/pdf',
                    as_attachment=False,
                    download_name='receipt.pdf'
                )

            elif output_type == 'print':
                odt_buffer = process_odt_template(booking_id, teacher, class_name, value, payment_type)
                pdf_buffer = convert_odt_to_pdf(odt_buffer)
                job_id = print_pdf_via_cups(pdf_buffer, cups_queue_name=cups_queue_name)
                return jsonify({'status': 'printed', 'job_id': job_id, 'printer': cups_queue_name})
                
            else:
                api.abort(400, f"Invalid output_type: {output_type}. Must be one of: svg, odt, pdf, print")
            
        except Exception as e:
            api.abort(500, str(e))

@api.route('/api/printer-status')
class PrinterStatus(Resource):
    @api.doc('printer_status')
    def get(self):
        """List CUPS printers for the printer selection dialog"""
        try:
            return jsonify({'printers': get_cups_printers()})
        except Exception as e:
            api.abort(500, str(e))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8087, debug=True)
