"""
Load Balancing Broker Pattern Implementation for Proyecto_SDF
Based on the ZeroMQ Load Balancing Broker Pattern

This module implements a broker that:
1. Connects clients (facultad instances) with workers (DTI_servidor instances)
2. Distributes work using a load balancing algorithm based on distance
3. Tracks and displays the count of remaining client requests
4. Manages worker availability 

The broker uses a ROUTER-ROUTER pattern with two separate sockets:
- Frontend: Communicates with clients (facultad instances)
- Backend: Communicates with workers (DTI_servidor instances)
"""

import zmq
import threading
import time
import json
import logging
from datetime import datetime
from config import BROKER_FRONTEND_URL, BROKER_BACKEND_URL
import sys

class LoadBalancerBroker:
    def __init__(self):
        """Initialize the load balancing broker"""
        self.context = zmq.Context()
        # Socket facing clients (facultad)
        self.frontend = self.context.socket(zmq.ROUTER)
        self.frontend.bind(BROKER_FRONTEND_URL)
        
        # Socket facing workers (DTI_servidor)
        self.backend = self.context.socket(zmq.ROUTER)
        self.backend.bind(BROKER_BACKEND_URL)
        
        # Queue of available workers
        self.available_workers = []
        
        # Track active workers
        self.workers = set()
        
        # Track client requests and their distances
        self.clients = {}
        self.client_requests_count = 0
        
        # Set up logging
        self.setup_logging()
        
        self.running = True
    
    def setup_logging(self):
        """Configure logging for the broker"""
        logging.basicConfig(
            filename="broker.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
    def start(self):
        """Start the broker's main loop"""
        print("✅ Load Balancer Broker iniciado")
        print(f"📡 Frontend escuchando en {BROKER_FRONTEND_URL}")
        print(f"📡 Backend escuchando en {BROKER_BACKEND_URL}")
        print("💡 Escriba 'salir' para terminar")
        
        # Start the monitoring thread
        self.monitor_thread = threading.Thread(target=self.monitor_function, daemon=True)
        self.monitor_thread.start()
        
        # Input thread for commands
        self.input_thread = threading.Thread(target=self.command_input, daemon=True)
        self.input_thread.start()
        
        try:
            self.broker_loop()
        except KeyboardInterrupt:
            print("\n🛑 Deteniendo Broker...")
        finally:
            self.cleanup()
    
    def command_input(self):
        """Handle command input in a separate thread"""
        while self.running:
            cmd = input().strip().lower()
            if cmd == "salir":
                self.running = False
                break
                
    def broker_loop(self):
        """Main broker loop using zmq polling"""
        # Initialize poll set
        poller = zmq.Poller()
        poller.register(self.frontend, zmq.POLLIN)
        poller.register(self.backend, zmq.POLLIN)
        
        while self.running:
            try:
                socks = dict(poller.poll(100))  # 100ms timeout for checking self.running
                
                # Handle worker messages
                if self.backend in socks and socks[self.backend] == zmq.POLLIN:
                    self.handle_worker_message()
                    
                # Handle client messages if workers are available
                if self.frontend in socks and socks[self.frontend] == zmq.POLLIN and self.available_workers:
                    self.handle_client_message()
            except Exception as e:
                logging.error(f"Error en loop principal: {e}")
    
    def handle_worker_message(self):
        """Process messages from workers"""
        # Worker address frames come first
        frames = self.backend.recv_multipart()
        
        # At least 3 frames expected: worker address, empty delimiter, client address
        if len(frames) < 3:
            worker_address = frames[0]
            # New worker registration
            self.available_workers.append(worker_address)
            self.workers.add(worker_address)
            logging.info(f"Nuevo trabajador registrado: {worker_address}")
            return
            
        # Existing worker sending a response
        worker_address = frames[0]
        empty = frames[1]         # Empty delimiter frame
        client_address = frames[2]
        
        # Rest of the frames are the actual response
        rest_frames = frames[3:]
        
        # Add the worker back to the available worker queue
        self.available_workers.append(worker_address)
        
        # Update clients count if this is completing a request
        if client_address in self.clients:
            self.client_requests_count -= 1
            
            # Extract the response data to log
            try:
                response_data = json.loads(rest_frames[-1])
                if "facultad" in response_data:
                    logging.info(f"Respuesta enviada a: {response_data['facultad']} - {response_data['programa']}")
            except:
                pass
        
        # Forward the response to the client
        try:
            # Asegurémonos de que la respuesta sea un JSON válido
            if rest_frames and isinstance(rest_frames[-1], bytes):
                try:
                    # Intentar parsear para verificar que es un JSON válido
                    json_data = json.loads(rest_frames[-1].decode('utf-8'))
                    # Si llega aquí, el JSON es válido
                except json.JSONDecodeError:
                    # Si no es un JSON válido, enviar un mensaje de error formateado
                    logging.error(f"Respuesta inválida del trabajador: {rest_frames[-1]}")
                    error_response = json.dumps({"error": "Respuesta inválida del servidor"}).encode('utf-8')
                    rest_frames[-1] = error_response
            
            # Enviar la respuesta al cliente
            self.frontend.send_multipart([client_address, empty] + rest_frames)
            logging.info(f"Respuesta enviada al cliente {client_address}")
        except Exception as e:
            logging.error(f"Error al reenviar respuesta al cliente: {e}")
            # Intentar enviar un mensaje de error en caso de fallo
            try:
                error_msg = json.dumps({"error": f"Error interno del broker: {str(e)}"}).encode('utf-8')
                self.frontend.send_multipart([client_address, empty, error_msg])
            except:
                logging.error("No se pudo enviar mensaje de error al cliente")
    
    def handle_client_message(self):
        """Process messages from clients"""
        # Client request format: [client_address, '', request]
        frames = self.frontend.recv_multipart()
        
        # Extract client info
        client_address = frames[0]
        request = frames[2]
        
        try:
            # Parse the request to extract faculty info for logging
            request_data = json.loads(request)
            
            # Get or calculate client distance (for load balancing)
            if client_address not in self.clients:
                # Assign a distance based on faculty name (simulated)
                faculty_name = request_data.get("facultad", "")
                # Simple hash-based distance to simulate physical distance
                distance = sum(ord(c) for c in faculty_name) % 10 + 1
                self.clients[client_address] = {
                    "faculty": faculty_name,
                    "distance": distance,
                    "first_seen": datetime.now(),
                    "requests": 0
                }
            
            # Update client stats
            self.clients[client_address]["requests"] += 1
            self.client_requests_count += 1
            
            # Log the request
            faculty = request_data.get("facultad", "unknown")
            program = request_data.get("programa", "unknown")
            logging.info(f"Solicitud recibida de: {faculty} - {program}")
        except:
            pass
        
        # Get next available worker using load balancing
        worker_address = self.get_next_worker()
        
        # Forward message to worker
        self.backend.send_multipart([worker_address, b''] + frames)
    
    def get_next_worker(self):
        """Select the next worker using a simple load balancing algorithm"""
        if not self.available_workers:
            raise Exception("No workers available")
        
        # Basic round-robin for now
        return self.available_workers.pop(0)
    
    def monitor_function(self):
        """Monitor function to display system status"""
        while self.running:
            sys.stdout.write(f"\r📊 Clientes activos: {len(self.clients)} | "
                           f"Trabajadores disponibles: {len(self.available_workers)}/{len(self.workers)} | "
                           f"Solicitudes pendientes: {self.client_requests_count}")
            sys.stdout.flush()
            time.sleep(1)
            
    def cleanup(self):
        """Clean up resources on exit"""
        self.frontend.close()
        self.backend.close()
        self.context.term()

if __name__ == "__main__":
    broker = LoadBalancerBroker()
    broker.start()
