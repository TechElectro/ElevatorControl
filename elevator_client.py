# elevator_client.py
import socket
import struct

# --- Configuración del Controlador ---
# Deberás cambiar esto por la IP y puerto de tu controlador
CONTROLLER_IP = "192.168.0.100"  # IP de tu dispositivo
CONTROLLER_PORT = 60000          # Puerto TCP del dispositivo

# --- Funciones de Utilidad del Protocolo ---

def calculate_checksum(data):
    """
    Calcula el checksum (verificación) usando un XOR simple sobre todos los bytes.
    [cite: 58, 59]
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
    # STX, Rand, Command, Address, Door, LengthL, LengthH
    frame_header = bytearray([stx, rand, command, address, door, length_l, length_h])
    frame_without_cs = frame_header + data

    # Calcula el checksum de todo el paquete [cite: 59]
    cs = calculate_checksum(frame_without_cs)
    
    # Añade CS y ETX
    frame_with_cs = frame_without_cs + bytearray([cs])
    final_frame = frame_with_cs + bytearray([0x03]) # ETX 
    
    return final_frame

def send_command(frame):
    """
    Se conecta al controlador, envía el comando y espera una respuesta.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)  # 5 segundos de timeout
            s.connect((CONTROLLER_IP, CONTROLLER_PORT))
            s.sendall(frame)
            response = s.recv(1024)
            
            # Un parseo de respuesta muy simple
            # La respuesta de éxito generalmente tiene 0x06 en el campo de datos [cite: 67]
            if response and response[7] == 0x06:
                return True, "Éxito"
            else:
                # La respuesta de fallo generalmente tiene 0x15 [cite: 68]
                return False, f"Fallo o respuesta desconocida: {response.hex()}"

    except socket.timeout:
        return False, "Error: Timeout (no se pudo conectar al controlador)"
    except Exception as e:
        return False, f"Error de conexión: {str(e)}"

# --- Funciones de Comando Específicas ---

def open_specific_door(door_id=1):
    """
    Implementa el Comando: 0x2C (Abrir Puerta)
    Este comando es simple y no tiene cuerpo de datos (Data).
    [cite: 239, 241]
    """
    print(f"Intentando abrir la puerta {door_id}...")
    command = 0x2C
    address = 0x00  # Dirección del controlador (asumimos 0)
    door = door_id  # El PDF dice que Door indica el relé (1 = relé 1) [cite: 241]
    data = b''      # No hay sección de datos para este comando [cite: 241]

    frame = build_frame(command, address, door, data)
    return send_command(frame)

def add_card_extended(card_info):
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