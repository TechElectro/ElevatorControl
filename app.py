# app.py
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS  # Necesitarás 'pip install Flask-Cors'
import elevator_client

app = Flask(__name__)
# Habilitar CORS para permitir que el frontend llame al backend
CORS(app) 

@app.route('/')
def index():
    """Sirve la página principal del frontend."""
    return render_template('index.html')

@app.route('/api/open-door', methods=['POST'])
def api_open_door():
    """
    Endpoint de API para abrir una puerta.
    """
    data = request.json
    door_id = int(data.get('door', 1)) # Obtiene el ID de la puerta, por defecto 1
    
    success, message = elevator_client.open_specific_door(door_id)
    
    if success:
        return jsonify({"status": "success", "message": f"Comando 'Abrir Puerta {door_id}' enviado."})
    else:
        return jsonify({"status": "error", "message": message}), 500

@app.route('/api/add-card', methods=['POST'])
def api_add_card():
    """
    Endpoint de API para agregar una nueva tarjeta.
    """
    card_info = request.json
    
    # Validación simple (puedes agregar más)
    if not all(k in card_info for k in ('card_id', 'card_number', 'floors', 'name')):
        return jsonify({"status": "error", "message": "Faltan datos (card_id, card_number, floors, name)"}), 400
        
    success, message = elevator_client.add_card_extended(card_info)
    
    if success:
        return jsonify({"status": "success", "message": f"Tarjeta '{card_info['name']}' agregada."})
    else:
        return jsonify({"status": "error", "message": message}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)