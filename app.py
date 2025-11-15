# app.py
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import multiprocessing # ¡Importante!
import elevator_service  # ¡Importante!

# --- Configuración del Proceso de Fondo ---
# Necesitamos una "Cola" para que Flask hable con el servicio de TCP
command_queue = multiprocessing.Queue()

app = Flask(__name__)
CORS(app) 

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/open-door', methods=['POST'])
def api_open_door():
    """
    Endpoint de API para abrir una puerta.
    ¡ESTO YA NO USA SOCKET! Solo pone un comando en la cola.
    """
    data = request.json
    door_id = int(data.get('door', 1))
    
    try:
        # Poner el comando en la cola para que el servicio lo maneje
        command_queue.put({'action': 'open_door', 'door': door_id})
        return jsonify({"status": "success", "message": f"Comando 'Abrir Puerta {door_id}' enviado al servicio."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error al enviar a la cola: {str(e)}"}), 500


@app.route('/api/add-card', methods=['POST'])
def api_add_card():
    """
    Endpoint de API para agregar una nueva tarjeta.
    """
    card_info = request.json
    
    # Validación simple (puedes mejorarla)
    if not all(k in card_info for k in ('card_id', 'card_number', 'floors', 'name')):
        return jsonify({"status": "error", "message": "Faltan datos (card_id, card_number, floors, name)"}), 400
        
    try:
        # --- ¡LÍNEA MODIFICADA! ---
        # Poner el comando en la cola para que el servicio lo maneje
        command_queue.put({'action': 'add_card', 'data': card_info})
        
        return jsonify({"status": "success", "message": f"Comando 'Agregar Tarjeta {card_info['name']}' enviado al servicio."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error al enviar a la cola: {str(e)}"}), 500

# ... (después de la función api_add_card) ...

@app.route('/api/delete-card/<int:card_id>', methods=['DELETE'])
def api_delete_card(card_id):
    """
    Endpoint de API para eliminar una tarjeta por su ID.
    Recibe el ID desde la URL.
    """
    if card_id <= 0:
        return jsonify({"status": "error", "message": "ID de tarjeta no válido"}), 400

    try:
        # Poner el comando en la cola para que el servicio lo maneje
        command_queue.put({'action': 'delete_card', 'card_id': card_id})
        
        return jsonify({"status": "success", "message": f"Comando 'Eliminar Tarjeta {card_id}' enviado al servicio."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error al enviar a la cola: {str(e)}"}), 500


if __name__ == '__main__':
    # --- ¡Magia! ---
    # 1. Iniciar el servicio de ascensor en un PROCESO SEPARADO
    print("Iniciando servicio de ascensor en segundo plano...")
    service_process = multiprocessing.Process(
        target=elevator_service.start_service, 
        args=(command_queue,)
    )
    service_process.daemon = True # Para que se cierre si Flask se cierra
    service_process.start()
    
    # 2. Iniciar la aplicación Flask (en el proceso principal)
    print("Iniciando servidor web Flask...")
    app.run(debug=False, host='0.0.0.0', port=5000)