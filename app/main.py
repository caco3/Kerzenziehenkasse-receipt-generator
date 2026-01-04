from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import io
import zipfile
import tempfile
import os
import xml.etree.ElementTree as ET
from datetime import datetime
import subprocess
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

def process_odt_template(booking_id, teacher, class_name, value, payment_type):
    """Process ODT template by replacing placeholders and QR code"""
    # Get current date and time
    now = datetime.now()
    current_year = now.year
    current_time = now.strftime("%H:%M")
    current_date = now.strftime("%d.%m.%Y")
    
    # Generate QR Bill SVG
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
    
    # Generate SVG to string
    svg_buffer = io.StringIO()
    bill.as_svg(svg_buffer)
    svg_data = svg_buffer.getvalue()
    svg_buffer.close()
    
    # Create temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        odt_template_path = '/templates/receipt.odt'
        
        # Extract ODT template
        with zipfile.ZipFile(odt_template_path, 'r') as template_zip:
            template_zip.extractall(temp_dir)
        
        # Replace SVG file in Pictures folder
        pictures_dir = os.path.join(temp_dir, 'Pictures')
        svg_files = [f for f in os.listdir(pictures_dir) if f.endswith('.svg')]
        if svg_files:
            svg_path = os.path.join(pictures_dir, svg_files[0])
            with open(svg_path, 'w', encoding='utf-8') as f:
                f.write(svg_data)
        
        # Replace placeholders in content.xml
        content_xml_path = os.path.join(temp_dir, 'content.xml')
        with open(content_xml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
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
        
        # Check the appropriate payment type checkbox
        if payment_type.lower() == 'bar':
            content = content.replace('<form:checkbox form:name="Bar"', '<form:checkbox form:name="Bar" form:current-state="checked"')
        elif payment_type.lower() == 'twint':
            content = content.replace('<form:checkbox form:name="Twint"', '<form:checkbox form:name="Twint" form:current-state="checked"')
        elif payment_type.lower() == 'ezs':
            content = content.replace('<form:checkbox form:name="Einzahlungsschein"', '<form:checkbox form:name="Einzahlungsschein" form:current-state="checked"')
        
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
CORS(app)  # Enable CORS for all routes

@app.route('/')
def index():
    """Simple API documentation page"""
    try:
        with open(os.path.join(os.path.dirname(__file__), 'index.html'), 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return '''
<!DOCTYPE html>
<html>
<head><title>Receipt Generator API</title></head>
<body>
    <h1>Receipt Generator API</h1>
    <p>Documentation file not found. Please check the API endpoints:</p>
    <ul>
        <li><strong>POST</strong> /api/generate-receipt - Generate receipts</li>
        <li><strong>GET</strong> /api/printer-status - Check printer status</li>
    </ul>
</body>
</html>
        '''

# Simple Flask route for receipt generation (bypassing flask-restx CORS issues)
@app.route('/api/generate-receipt', methods=['POST', 'OPTIONS'])
def generate_receipt_flask():
    """Generate receipt based on output type - Flask route version"""
    if request.method == 'OPTIONS':
        return '', 200
        
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
            # Generate QR Bill as SVG
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
            
            svg_bytes = io.BytesIO(svg_data.encode('utf-8'))
            svg_bytes.seek(0)
            return send_file(
                svg_bytes,
                mimetype='image/svg+xml',
                as_attachment=False,
                download_name=f'receipt-{booking_id}.svg'
            )
            
        elif output_type == 'odt':
            odt_buffer = process_odt_template(booking_id, teacher, class_name, value, payment_type)
            return send_file(
                odt_buffer,
                mimetype='application/vnd.oasis.opendocument.text',
                as_attachment=False,
                download_name=f'receipt-{booking_id}.odt'
            )
            
        elif output_type == 'pdf':
            odt_buffer = process_odt_template(booking_id, teacher, class_name, value, payment_type)
            pdf_buffer = convert_odt_to_pdf(odt_buffer)
            return send_file(
                pdf_buffer,
                mimetype='application/pdf',
                as_attachment=False,
                download_name=f'receipt-{booking_id}.pdf'
            )

        elif output_type == 'print':
            odt_buffer = process_odt_template(booking_id, teacher, class_name, value, payment_type)
            pdf_buffer = convert_odt_to_pdf(odt_buffer)
            job_id = print_pdf_via_cups(pdf_buffer, cups_queue_name=cups_queue_name)
            return jsonify({'status': 'printed', 'job_id': job_id, 'printer': cups_queue_name})
            
        else:
            return jsonify({'error': f"Invalid output_type: {output_type}. Must be one of: svg, odt, pdf, print"}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Printer status check endpoint
@app.route('/api/printer-status', methods=['GET'])
def printer_status():
    """Check status of available printers"""
    try:
        import subprocess
        
        # Get all printer information
        result = subprocess.run(['lpstat', '-v'], capture_output=True, text=True)
        if result.returncode != 0:
            return jsonify({'error': 'Failed to get printer information'}), 500
        
        printers = []
        lines = result.stdout.strip().split('\n')
        
        for line in lines:
            if 'device for' in line or 'Gerät für' in line:
                # Parse printer info: "device for printer_name: device_uri" or "Gerät für printer_name: device_uri"
                if 'device for' in line:
                    parts = line.split('device for ')[1].split(': ', 1)
                else:
                    parts = line.split('Gerät für ')[1].split(': ', 1)
                if len(parts) >= 2:
                    printer_name = parts[0]
                    device_uri = parts[1]
                    
                    # Check if printer is accepting jobs and get description
                    try:
                        status_result = subprocess.run(['lpstat', '-l', '-p', printer_name], capture_output=True, text=True)
                        is_enabled = 'enabled' in status_result.stdout.lower()
                        status = 'enabled' if is_enabled else 'disabled'
                        
                        # Extract printer description using lpstat
                        description = ''
                        for line in status_result.stdout.split('\n'):
                            if 'description:' in line.lower():
                                desc_pos = line.lower().find('description:')
                                if desc_pos != -1:
                                    description = line[desc_pos + 12:].strip()
                                break
                    except Exception as e:
                        status = 'unknown'
                        description = ''
                    
                    # Extract IP from device URI if it's a network printer
                    ip_address = None
                    if 'ipp://' in device_uri:
                        ip_address = device_uri.split('ipp://')[1].split('/')[0]
                    elif 'dnssd://' in device_uri:
                        # For DNS-SD printers, we can't easily get IP without additional resolution
                        ip_address = None
                    
                    printers.append({
                        'name': printer_name,
                        'device_uri': device_uri,
                        'status': status,
                        'ip_address': ip_address,
                        'type': 'network' if ip_address else 'local',
                        'description': description
                    })
        
        return jsonify({
            'printers': printers,
            'total_count': len(printers)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
