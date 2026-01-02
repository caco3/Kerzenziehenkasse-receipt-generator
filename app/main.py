from flask import Flask, jsonify, request, send_file
import io
from flask_restx import Api, Resource, fields
from qrbill import QRBill

# Account data
iban = "CH05 0688 8016 1232 5000 7"
name = "Viva Kirche Schweiz"
street = "Kirche Neuwies Uster"
postal_code = 4126
city = "Bettingen"

app = Flask(__name__)
api = Api(app, version='1.0', title='QR Bill Generator API',
          description='API for generating Swiss QR bills with predefined account information',
          doc='/', default='api', default_label='QR Bill API')

# Model for QR generation request
qr_request_model = api.model('QRRequest', {
    'value': fields.String(required=False, description='Payment amount', default='56.70'),
    'additional_information': fields.String(required=False, description='Reference/additional information', default='Kerzenziehen 1234')
})

# Model for receipt generation request (duplicate of QR request)
receipt_request_model = api.model('ReceiptRequest', {
    'value': fields.String(required=False, description='Payment amount', default='56.70'),
    'additional_information': fields.String(required=False, description='Reference/additional information', default='Kerzenziehen 1234')
})

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'healthy'}

@api.route('/api/generate-qr')
class GenerateQR(Resource):
    @api.doc('generate_qr_bill')
    @api.expect(qr_request_model)
    def post(self):
        """Generate Swiss QR Bill as SVG image"""
        try:
            data = request.get_json()
            
            # Get value and additional information from request
            value = data.get('value', '0.0')
            additional_info = data.get('additional_information', '')
            
            # Create QR bill with predefined account info
            bill = QRBill(
                account=iban,
                creditor={
                    'name': name,
                    'street': street,
                    'pcode': str(postal_code),
                    'city': city,
                    'country': 'CH'
                },
                amount=value,
                currency='CHF',
                additional_information=additional_info,
                language='de'
            )
            
            # Generate SVG
            svg_buffer = io.StringIO()
            bill.as_svg(svg_buffer)
            svg_data = svg_buffer.getvalue()
            svg_buffer.close()
            
            # Return as SVG file using send_file to avoid escaping
            svg_bytes = io.BytesIO(svg_data.encode('utf-8'))
            svg_bytes.seek(0)
            return send_file(
                svg_bytes,
                mimetype='image/svg+xml',
                as_attachment=False,
                download_name='qr-bill.svg'
            )
            
        except Exception as e:
            api.abort(500, str(e))

@api.route('/api/generate-receipt')
class GenerateReceipt(Resource):
    @api.doc('generate_receipt')
    @api.expect(receipt_request_model)
    def post(self):
        """Generate receipt as SVG image"""
        try:
            data = request.get_json()
            
            # Get value and additional information from request
            value = data.get('value', '0.0')
            additional_info = data.get('additional_information', '')
            
            # Create QR bill with predefined account info (same as QR generation)
            bill = QRBill(
                account=iban,
                creditor={
                    'name': name,
                    'street': street,
                    'pcode': str(postal_code),
                    'city': city,
                    'country': 'CH'
                },
                amount=value,
                currency='CHF',
                additional_information=additional_info,
                language='de'
            )
            
            # Generate SVG
            svg_buffer = io.StringIO()
            bill.as_svg(svg_buffer)
            svg_data = svg_buffer.getvalue()
            svg_buffer.close()
            
            # Return as SVG file using send_file to avoid escaping
            svg_bytes = io.BytesIO(svg_data.encode('utf-8'))
            svg_bytes.seek(0)
            return send_file(
                svg_bytes,
                mimetype='image/svg+xml',
                as_attachment=False,
                download_name='receipt.svg'
            )
            
        except Exception as e:
            api.abort(500, str(e))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
