import socket
import threading
import time
from urllib.parse import urlparse

# Configuration
HOST = '127.0.0.1'  # Localhost
PORT = 8080         # Port to run the proxy on
DELAY = 1.0         # Delay in seconds per chunk of data
CHUNK_SIZE = 1024   # Size of data chunks to send

def handle_client(client_socket):
    request = client_socket.recv(4096)
    try:
        first_line = request.split(b'\r\n')[0]
        url = first_line.split(b' ')[1]
        parsed_url = urlparse(url.decode('utf-8'))

        host = parsed_url.hostname
        path = parsed_url.path + '?' + parsed_url.query if parsed_url.query else parsed_url.path
        if not path:
            path = '/'
        
        port = parsed_url.port if parsed_url.port else 80

        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.connect((host, port))
        remote_socket.send(request)  # Forward the original request

        while True:
            response = remote_socket.recv(CHUNK_SIZE)
            if not response:
                break

            if b'HTTP/1.1 301' in response:
                headers = response.split(b'\r\n')
                for header in headers:
                    if b'Location: ' in header:
                        new_url = header.split(b'Location: ')[1].strip()
                        print(f"Redirecting to {new_url.decode('utf-8')}")
                        return handle_client(client_socket)  # Recursive call with new URL
                        
            client_socket.send(response)  # Forward to client
            time.sleep(DELAY)  # Slow down response

        remote_socket.close()
    except Exception as e:
        print(f"Error: {e}")

    client_socket.close()



def start_proxy():
    print(f"Sloxy running on {HOST}:{PORT}, with a delay of {DELAY} seconds per {CHUNK_SIZE} bytes.")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr}")
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        client_handler.start()

if __name__ == "__main__":
    start_proxy()
