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
HOST = '127.0.0.1'  # Localhost
PORT = 8080         # Port to run the proxy on
DELAY = 1.0         # Delay in seconds per chunk of data
CHUNK_SIZE = 1024   # Size of data chunks to send
MEME_FOLDER = "memes"  # Folder containing meme images

def load_memes(folder):
    """
    Loads meme file paths from the given folder.
    Only files with valid image extensions are loaded.
    """
    memes = []
    try:
        for file in os.listdir(folder):
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                memes.append(os.path.join(folder, file))
    except Exception as e:
        print(f"Error loading memes from folder {folder}: {e}")
    return memes

# Global meme pool loaded at startup.
MEME_POOL = load_memes(MEME_FOLDER)

def overlay_meme_on_image(original_body):
    """
    Opens the original image from bytes and overlays the top 50% 
    with a meme image chosen randomly from MEME_POOL.
    
    Returns a tuple (modified_image_bytes, image_format) on success,
    or (None, None) if processing fails.
    """
    try:
        original_image = Image.open(BytesIO(original_body))
    except Exception as e:
        print("Error opening original image:", e)
        return None, None

    width, height = original_image.size
    half_height = height // 2

    if not MEME_POOL:
        print("Meme pool is empty!")
        return None, None

    meme_path = random.choice(MEME_POOL)
    try:
        meme_image = Image.open(meme_path)
    except Exception as e:
        print("Error opening meme image:", e)
        return None, None

    # Resize meme to match the original width and cover 50% of its height
    meme_resized = meme_image.resize((width, half_height))
    # Convert both images to RGBA for proper overlay
    original_image = original_image.convert("RGBA")
    meme_resized = meme_resized.convert("RGBA")
    
    # Paste the meme onto the top half of the original image.
    # The meme_resized fully covers that region.
    original_image.paste(meme_resized, (0, 0))
    
    # Save the modified image to a bytes buffer.
    output = BytesIO()
    # Use the original format if available; otherwise default to PNG.
    fmt = original_image.format if original_image.format is not None else "PNG"
    original_image.save(output, format=fmt)
    return output.getvalue(), fmt

def serve_easter_egg(client_socket):
    """
    When a request to google.ca is detected, serve a custom HTML page with an embedded meme.
    """
    if not MEME_POOL:
        client_socket.send(b"HTTP/1.1 404 Not Found\r\n\r\nNo memes available.")
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
        html_content = f"""
        <html>
        <head>
            <title>Surprise!</title>
            <meta charset="utf-8">
        </head>
        <body>
            <img src="data:{mime};base64,{b64_data}" style="width:100vw; height:auto; object-fit:cover;" alt="Easter Egg Meme"/>
        </body>
        </html>
        """
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
        client_socket.send(b"HTTP/1.1 500 Internal Server Error\r\n\r\n")
    client_socket.close()

def handle_client(client_socket):
    request = client_socket.recv(4096)
    if not request:
        client_socket.close()
        return
    try:
        first_line = request.split(b'\r\n')[0]
        parts = first_line.split(b' ')
        print(parts)
        if len(parts) < 2:
            client_socket.close()
            return
        url = parts[1].decode('utf-8')
        parsed_url = urlparse(url)

        # Easter egg for google.ca
        if parsed_url.hostname and parsed_url.hostname.lower() == "google.ca":
            return serve_easter_egg(client_socket)

        # If the request is for an image (based on its file extension),
        # fetch the original image from the remote server,
        # overlay 50% of it with a meme, and send the modified image.
        if parsed_url.path.lower().startswith('/image'):
            host = parsed_url.hostname
            path = parsed_url.path if parsed_url.path else '/'
            if parsed_url.query:
                path += '?' + parsed_url.query
            port = parsed_url.port if parsed_url.port else 80

            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.connect((host, port))
            remote_socket.send(request)

            # Buffer the entire response.
            response_data = b""
            while True:
                chunk = remote_socket.recv(CHUNK_SIZE)
                if not chunk:
                    break
                response_data += chunk
            remote_socket.close()

            # Split the HTTP response into headers and body.
            header_end = response_data.find(b'\r\n\r\n')
            if header_end == -1:
                client_socket.send(response_data)
                client_socket.close()
                return
            headers_bytes = response_data[:header_end]
            body = response_data[header_end+4:]

            # Modify the image: overlay the top half with a meme.
            modified_body, new_format = overlay_meme_on_image(body)
            if modified_body is None:
                client_socket.send(response_data)
                client_socket.close()
                return

            # Update headers: adjust Content-Length and (if needed) Content-Type.
            # Update headers: adjust Content-Length and (if needed) Content-Type.
            headers_lines = headers_bytes.split(b'\r\n')
            new_headers_lines = []
            content_type_set = False

            for line in headers_lines:
                if line.lower().startswith(b"content-length:"):
                    new_headers_lines.append(b"Content-Length: " + str(len(modified_body)).encode('utf-8'))
                elif line.lower().startswith(b"content-type:"):
                    content_type_set = True
                    if new_format.lower() in ("png"):
                        new_headers_lines.append(b"Content-Type: image/png")
                    elif new_format.lower() in ("jpg", "jpeg"):
                        new_headers_lines.append(b"Content-Type: image/jpeg")
                    elif new_format.lower() == "gif":
                        new_headers_lines.append(b"Content-Type: image/gif")
                    elif new_format.lower() == "webp":
                        new_headers_lines.append(b"Content-Type: image/webp")
                    else:
                        new_headers_lines.append(line)  # Keep original header if format isn't recognized
                else:
                    new_headers_lines.append(line)

            # Ensure a Content-Type header is set if it was missing
            if not content_type_set:
                if new_format.lower() in ("png"):
                    new_headers_lines.append(b"Content-Type: image/png")
                elif new_format.lower() in ("jpg", "jpeg"):
                    new_headers_lines.append(b"Content-Type: image/jpeg")
                elif new_format.lower() == "gif":
                    new_headers_lines.append(b"Content-Type: image/gif")
                elif new_format.lower() == "webp":
                    new_headers_lines.append(b"Content-Type: image/webp")

            new_headers = b'\r\n'.join(new_headers_lines)
            final_response = new_headers + b'\r\n\r\n' + modified_body
            client_socket.send(final_response)
            client_socket.close()
            return

        # For non-image requests, forward traffic normally.
        host = parsed_url.hostname
        if not host:
            client_socket.close()
            return

        path = parsed_url.path if parsed_url.path else '/'
        if parsed_url.query:
            path += '?' + parsed_url.query
        port = parsed_url.port if parsed_url.port else 80

        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.connect((host, port))
        remote_socket.send(request)

    except Exception as e:
        print(f"Error handling client: {e}")
    client_socket.close()
    return  

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
