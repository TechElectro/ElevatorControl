# elevator_service.py
import socket
import time
import select
import elevator_protocol  # Importamos nuestro constructor de tramas

# --- Configuración ---
CONTROLLER_IP = "192.168.1.170"  # ¡CAMBIA ESTO!
CONTROLLER_PORT = 8000

class ElevatorService:
    def __init__(self, command_queue):
        self.command_queue = command_queue
        self.sock = None
        self.connect()

    def connect(self):
        while True:
            try:
                print("Servicio: Intentando conectar al controlador...")
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(10.0)
                self.sock.connect((CONTROLLER_IP, CONTROLLER_PORT))
                self.sock.setblocking(True) # ¡Importante! Modo no bloqueante
                print("Servicio: ¡Conectado al controlador!")
                break
            except Exception as e:
                print(f"Servicio: Error de conexión: {e}. Reintentando en 5s...")
                time.sleep(5)

    def handle_controller_data(self):
        try:
            data = self.sock.recv(1024)
            if not data:
                print("Servicio: Controlador desconectado.")
                return False # Señal de reconexión

            # --- ¡LÓGICA DE HEARTBEAT! ---
            # Un parseo simple: asumimos que el 3er byte es el comando
            command_byte = data[2] 
            
            if command_byte == 0x56: # [cite: 83]
                print("Servicio: Heartbeat (0x56) recibido del controlador.")
                # Respondemos inmediatamente al heartbeat
                reply_frame = elevator_protocol.build_heartbeat_reply_frame()
                self.sock.sendall(reply_frame)
                print("Servicio: Respuesta de Heartbeat enviada.")
            else:
                print(f"Servicio: Recibido comando desconocido {hex(command_byte)}: {data.hex()}")
            
        except BlockingIOError:
            # Esto es normal, significa que no había datos que leer
            pass
        except Exception as e:
            print(f"Servicio: Error en handle_controller_data: {e}")
            return False # Señal de reconexión
        
        return True # Todo bien

    def handle_web_command(self):
        try:
            # Revisar si Flask (app.py) nos envió un comando
            command = self.command_queue.get_nowait()
            
            if command['action'] == 'open_door':
                door_id = command['door']
                print(f"Servicio: Recibida orden de Flask: Abrir Puerta {door_id}")
                frame = elevator_protocol.build_open_door_frame(door_id)
                self.sock.sendall(frame)
                print("Servicio: Comando (0x2C) enviado al controlador.")
            
            # --- ¡NUEVO BLOQUE! ---
            elif command['action'] == 'add_card':
                card_info = command['data']
                print(f"Servicio: Recibida orden de Flask: Agregar Tarjeta {card_info['name']}")
                
                frame = elevator_protocol.build_add_card_frame(card_info)
                
                if frame:
                    self.sock.sendall(frame)
                    print("Servicio: Comando (0xC1) enviado al controlador.")
                else:
                    print("Servicio: Error, trama de 'add_card' no válida. No se envió.")
            # --- FIN DEL NUEVO BLOQUE ---

        except Exception as e:
            # La cola estaba vacía, es normal.
            pass

    def run_forever(self):
        while True:
            # Usamos select para escuchar el socket y la cola
            # (Aunque la cola es más simple de revisar directamente)
            
            # 1. Escuchar al controlador (para heartbeats)
            connected = self.handle_controller_data()
            if not connected:
                self.connect() # Si se desconecta, reconectar
            
            # 2. Escuchar a Flask (para comandos web)
            self.handle_web_command()
            
            # No sobrecargar la CPU
            time.sleep(0.01) 

def start_service(queue):
    # Esta función se ejecutará en un proceso separado
    service = ElevatorService(queue)
    service.run_forever()