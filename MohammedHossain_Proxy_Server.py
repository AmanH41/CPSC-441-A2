import socket
import threading
import time
import random
import os
import base64
from urllib.parse import urlparse
from io import BytesIO
from PIL import Image

# Configuration
HOST = '127.0.0.1'      # Localhost
PORT = 8080             # Port to run the proxy on
DELAY = 1.0             # Delay in seconds per chunk of data
CHUNK_SIZE = 1024       # Size of data chunks to send
MEME_FOLDER = "memes"   # Folder containing meme images

def load_memes(folder):
    # Loads meme file paths from the given folder. 
    # Only files with valid image extensions are loaded.
    memes = []
    try:
        for file in os.listdir(folder):
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                memes.append(os.path.join(folder, file))
    except Exception as e:
        print(f"Error loading memes from folder {folder}: {e}")
    return memes

# Global meme pool loaded at startup.
MEME_POOL = load_memes(MEME_FOLDER)

def serve_meme_image(client_socket):
    #    read a meme image from folder and build a new HTTP response with its contents.   
    if not MEME_POOL:
        client_socket.send(b"HTTP/1.1 404 Not Found\r\n\r\n")
        client_socket.close()
        return

    meme_path = random.choice(MEME_POOL)
    try:
        with open(meme_path, "rb") as f:
            meme_data = f.read()        #store file in binary mode 
    except Exception as e:
        print("Error opening meme image:", e)
        client_socket.send(b"HTTP/1.1 500 Internal Server Error\r\n\r\n")
        client_socket.close()
        return

    # Determine Content-Type based on file extension
    ext = os.path.splitext(meme_path)[1].lower()
    if ext in ['.jpg', '.jpeg']:
        content_type = "image/jpeg"
    elif ext == '.png':
        content_type = "image/png"
    elif ext == '.gif':
        content_type = "image/gif"
    elif ext == '.webp':
        content_type = "image/webp"
    else:
        content_type = "application/octet-stream"

    # Build and send the HTTP response with new meme image as body.
    response = (
        "HTTP/1.1 200 OK\r\n"
        f"Content-Type: {content_type}\r\n"                 #content type based on meme file extension 
        f"Content-Length: {len(meme_data)}\r\n"             #the length of the meme data in btytes 
        "\r\n"
    ).encode('utf-8') + meme_data
    client_socket.send(response)
    client_socket.close()

def serve_easter_egg(client_socket):
    # When request to google.ca is detected serve cutom html page with meme 
    if not MEME_POOL:
        client_socket.send(b"404 Not Found\r\n\r\n")
        client_socket.close()
        return

    meme_path = random.choice(MEME_POOL)
    try:
        with open(meme_path, "rb") as f:
            meme_data = f.read()
        ext = os.path.splitext(meme_path)[1].lower()
        if ext in ['.jpg', '.jpeg']:
            mime = "image/jpeg"
        elif ext == '.png':
            mime = "image/png"
        elif ext == '.gif':
            mime = "image/gif"
        else:
            mime = "application/octet-stream"
        b64_data = base64.b64encode(meme_data).decode('utf-8')
        # Constructs an HTML page that embeds the image directly via a data URL.
        html_content = f"""
        <html>
        <head>
            <title>Ester Egg</title>
            <meta charset="utf-8">
        </head>
        <body>
            <img src="data:{mime};base64,{b64_data}" style="width:100vw; height:auto; object-fit:cover; content-align:center" alt="Easter Egg"/>
        </body>
        </html>
        """
        #Constructs an HTTP response
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html\r\n"
            f"Content-Length: {len(html_content.encode('utf-8'))}\r\n"
            "\r\n"
            f"{html_content}"
        )
        client_socket.send(response.encode('utf-8'))
    except Exception as e:
        print(f"Error serving easter egg: {e}")
        client_socket.send(b"500 Internal Server Error\r\n\r\n")
    client_socket.close()

def handle_client(client_socket):
    #read incoming HTTP request 
    request = client_socket.recv(4096)
    if not request:
        client_socket.close()
        return
    try:
        #split the HTTP Request and obtain the method and url 
        first_line = request.split(b'\r\n')[0]
        parts = first_line.split(b' ')
        if len(parts) < 2:
            client_socket.close()
            return
        url = parts[1].decode('utf-8')
        parsed_url = urlparse(url)

        # Easter egg for google.ca
        if parsed_url.hostname and parsed_url.hostname.lower() == "google.ca":
            serve_easter_egg(client_socket)
            return

        # If the request is for an image endpoint, ignore the original image
        # and serve a meme image from meme foldere instead.
        if parsed_url.path.lower().startswith('/image'):
            serve_meme_image(client_socket)
            return

        # For non-image requests forward traffic normally 
        host = parsed_url.hostname
        if not host:
            client_socket.close()
            return

        #build path and determine portt (defaulting to 80)
        path = parsed_url.path if parsed_url.path else '/'
        if parsed_url.query:
            path += '?' + parsed_url.query
        port = parsed_url.port if parsed_url.port else 80

        #open a new socket to the target hostt tand port 
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.connect((host, port))
        #send the request 
        remote_socket.send(request)

        while True:
            response = remote_socket.recv(CHUNK_SIZE)
            if not response:
                break
            client_socket.send(response)
            time.sleep(DELAY)
        remote_socket.close()
    except Exception as e:
        print(f"Error handling client: {e}")
    client_socket.close()

def start_proxy():
    print(f"Proxy running on {HOST}:{PORT}, with a delay of {DELAY} seconds per {CHUNK_SIZE} bytes.")
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
