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

# Model for receipt generation request
receipt_request_model = api.model('ReceiptRequest', {
    'value': fields.Float(required=True, description='Payment amount'),
    'booking_id': fields.Integer(required=True, description='Reference/additional information'),
    'teacher': fields.String(required=True, description='Teacher name'),
    'class': fields.String(required=True, description='Class name'),
    'payment_type': fields.String(required=True, description='Payment type (bar, Twint, Einzahlungsschein)'),
    'output_type': fields.String(required=True, description='Output type: svg, odt, pdf')
})

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'healthy'}

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
            
            if output_type == 'svg':
                # Generate QR Bill as SVG
                additional_info = "Kerzenziehen " + str(booking_id)
                
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
                    amount=str(value),
                    currency='CHF',
                    additional_information=additional_info,
                    language='de'
                )
                
                # Generate SVG
                svg_buffer = io.StringIO()
                bill.as_svg(svg_buffer)
                svg_data = svg_buffer.getvalue()
                svg_buffer.close()
                
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
                # TODO: Implement ODT generation
                api.abort(501, "ODT receipt generation not implemented yet")
                
            elif output_type == 'pdf':
                # TODO: Implement PDF generation
                api.abort(501, "PDF receipt generation not implemented yet")
                
            else:
                api.abort(400, f"Invalid output_type: {output_type}. Must be one of: svg, odt, pdf")
            
        except Exception as e:
            api.abort(500, str(e))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
