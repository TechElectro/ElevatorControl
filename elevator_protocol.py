# elevator_protocol.py
import struct

def calculate_checksum(data):
    """
    Calcula el checksum (verificación) usando un XOR simple sobre todos los bytes.
    """
    cs = 0
    for byte in data:
        cs ^= byte
    return cs

def build_frame(command, address, door, data=b''):
    """
    Construye la trama de bytes completa según la estructura del PDF.
    """
    stx = 0x02
    rand = 0x00  # "Reservado" según el PDF
    data_len = len(data)
    length_l = data_len & 0xFF
    length_h = (data_len >> 8) & 0xFF

    # Construye el frame sin CS y ETX primero
    frame_header = bytearray([stx, rand, command, address, door, length_l, length_h])
    frame_without_cs = frame_header + data

    cs = calculate_checksum(frame_without_cs)
    final_frame = frame_without_cs + bytearray([cs, 0x03]) # CS y ETX
    
    return final_frame

# --- Funciones Específicas para construir TRAMAS ---

def build_open_door_frame(door_id=1):
    """
    Construye la trama para el Comando: 0x2C (Abrir Puerta)
    """
    print(f"Construyendo trama para abrir puerta {door_id}...")
    command = 0x2C
    address = 0x00  # Asumimos 0
    door = door_id
    data = b''
    return build_frame(command, address, door, data)

def build_heartbeat_reply_frame():
    """
    Construye la trama de respuesta al Heartbeat 0x56.
    Según el PDF, la respuesta debe incluir un 'Pull Command' (序号).
    Si no tenemos comandos para 'empujar', enviamos un 0.
    """
    print("Construyendo respuesta de Heartbeat...")
    command = 0x56
    address = 0x00
    door = 0x00
    
    # Datos de respuesta (Página 6) [cite: 88]
    # customer_code_h, customer_code_l, reserved(2), pull_id(4), pull_data(0-N)
    
    # Simple respuesta sin 'pull command' (pull_id = 0)
    data = b'\x00\x00' + b'\x00\x00' + b'\x00\x00\x00\x00'
    
    # ¡OJO! El PDF dice que el 'LengthH' y 'LengthL' se invierten en la respuesta.
    # La función build_frame maneja esto, pero es un detalle clave.
    return build_frame(command, address, door, data)

# ... (Aquí iría build_add_card_frame, etc.) ...
    """
    Implementa el Comando: 0xC1 (Agregar Tarjeta - Versión Extendida)
    Este comando es complejo y requiere construir un cuerpo de datos (Data)
    con una estructura específica. 
    """
    print(f"Intentando agregar tarjeta...")

    command = 0xC1
    address = 0x00 # Dirección del controlador
    door = 0x00    # No aplica a una puerta específica

    # --- Construcción del Payload (Data)  ---
    # Esto debe coincidir exactamente con la tabla de la página 12.
    # Usamos 'struct.pack' para empaquetar los datos en bytes.
    
    try:
        # 3 bytes: Card ID (ej. 1, empaquetado como 3 bytes)
        card_id_bytes = int(card_info['card_id']).to_bytes(3, 'little')
        
        # 4 bytes: Card Number (ej. 12345678, empaquetado como 4 bytes LE)
        card_num_bytes = int(card_info['card_number']).to_bytes(4, 'little')
        
        # 9 bytes: QR Code (relleno si no se usa)
        qr_bytes = b'\x00' * 9
        
        # 18 bytes: ID Card (relleno si no se usa)
        id_bytes = b'\x00' * 18
        
        # 4 bytes: Password (BCD, 0xFFFFFFFFF si no se usa)
        pass_bytes = b'\xFF\xFF\xFF\xFF'
        
        # 8 bytes: Floors (bitmask, ej. 0x01 para piso 1, 0x03 para piso 1 y 2)
        floor_bytes = int(card_info['floors']).to_bytes(8, 'little')
        
        # 2 bytes: Door Permission (bitmask, ej. 0x01 para zona horaria 1)
        perm_bytes = b'\x01\x00'
        
        # 5 bytes: Expiry (Y-M-D-H-M, ej. 2030-12-31 23:59)
        # Año - 2000 
        expiry_bytes = bytearray([
            30, 12, 31, 23, 59
        ])
        
        # 8 bytes: Name (GB2312, rellenar con 0s)
        name_bytes = card_info['name'].encode('gb2312').ljust(8, b'\x00')

        # Empaquetamos todos los datos juntos
        data_payload = (
            card_id_bytes +
            card_num_bytes +
            qr_bytes +
            id_bytes +
            pass_bytes +
            floor_bytes +
            perm_bytes +
            expiry_bytes +
            name_bytes
        )

        frame = build_frame(command, address, door, data_payload)
        return send_command(frame)

    except Exception as e:
        return False, f"Error al construir la trama de la tarjeta: {str(e)}"
    

    # ... (después de la función build_heartbeat_reply_frame) ...

def build_add_card_frame(card_info):
    """
    Construye la trama para el Comando: 0xC1 (Añadir Tarjeta - Extendido) 
    """
    print(f"Construyendo trama para agregar tarjeta: {card_info['name']}")

    command = 0xC1
    address = 0x00 # Dirección del controlador
    door = 0x00    # No aplica

    # --- Construcción del Payload (Data) [cite: 131] ---
    # Esto debe coincidir exactamente con la tabla de la página 12.
    
    try:
        # 3 bytes: Card ID (ID único de tarjeta, ej. 1) [cite: 131]
        card_id_bytes = int(card_info['card_id']).to_bytes(3, 'little')
        
        # 4 bytes: Card Number (Número físico de la tarjeta) [cite: 131]
        card_num_bytes = int(card_info['card_number']).to_bytes(4, 'little')
        
        # 9 bytes: QR Code (relleno si no se usa) [cite: 131]
        qr_bytes = b'\x00' * 9
        
        # 18 bytes: ID Card (cédula) (relleno si no se usa) [cite: 131]
        id_bytes = b'\x00' * 18
        
        # 4 bytes: Password (BCD, 0xFFFFFFFFF si no se usa) [cite: 131]
        pass_bytes = b'\xFF\xFF\xFF\xFF'
        
        # 8 bytes: Floors (Bitmask para los pisos) [cite: 131]
        # Ej: 1 = piso 1, 3 = piso 1 y 2, 255 = pisos 1-8
        floor_bytes = int(card_info['floors']).to_bytes(8, 'little')
        
        # 2 bytes: Door Permission (Bitmask para zonas horarias) [cite: 131]
        # 0x01 0x00 = Usar la zona horaria 1
        perm_bytes = b'\x01\x00'
        
        # 5 bytes: Expiry (Año-Mes-Día-Hora-Minuto) [cite: 131]
        # Usamos una fecha lejana por defecto: 31-12-2030 23:59
        # Año (30 = 2030), Mes (12), Día (31), Hora (23), Min (59)
        expiry_bytes = bytearray([
            30, 12, 31, 23, 59
        ])
        
        # 8 bytes: Name (Codificado en GB2312) [cite: 131]
        # Rellenamos con \x00 si el nombre es más corto.
        name_bytes = card_info['name'].encode('gb2312').ljust(8, b'\x00')

        # Empaquetamos todos los datos juntos
        data_payload = (
            card_id_bytes +
            card_num_bytes +
            qr_bytes +
            id_bytes +
            pass_bytes +
            floor_bytes +
            perm_bytes +
            expiry_bytes +
            name_bytes
        )

        return build_frame(command, address, door, data_payload)

    except Exception as e:
        print(f"Error al construir la trama de la tarjeta: {e}")
        return None
    

    # ... (después de la función build_add_card_frame) ...

def build_delete_card_frame(card_id):
    """
    Construye la trama para el Comando: 0x15 (Eliminar una Tarjeta) 
    """
    print(f"Construyendo trama para eliminar tarjeta ID: {card_id}")

    command = 0x15  # 
    address = 0x00 # Dirección del controlador
    door = 0x00    # No aplica

    try:
        # El PDF (p12) especifica 4 bytes, "high bit in front" (big-endian) 
        data_payload = int(card_id).to_bytes(4, 'big')
        
        return build_frame(command, address, door, data_payload)

    except Exception as e:
        print(f"Error al construir la trama de eliminar tarjeta: {e}")
        return None