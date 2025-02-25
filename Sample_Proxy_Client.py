import socket
import os

def send_request(host, port, url):
    # Create a socket object
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Connect to the proxy server
    client_socket.connect((host, port))
    
    # Prepare the HTTP GET request
    request = f"GET {url} HTTP/1.1\r\nHost: testfile.org\r\nConnection: close\r\n\r\n"
    
    # Send the request to the proxy server
    client_socket.send(request.encode())
    
    # Receive the response from the proxy server
    response = b""
    while True:
        part = client_socket.recv(4096)
        if not part:
            break
        response += part
    
    # Attempt to split the response into headers and body
    parts = response.split(b'\r\n\r\n', 1)
    if len(parts) == 2:
        headers, body = parts
        filename = os.path.basename(url)
        if not filename:
            filename = "downloaded_file"

        with open(filename, 'wb') as file:
            file.write(body)
            print(f"File has been saved as {filename}")
    else:
        print("Unexpected response format.")


    # Close the socket
    client_socket.close()

if __name__ == "__main__":
    # Set the parameters for the proxy server
    HOST = '127.0.0.1'  # Localhost
    PORT = 8080         # Port of your proxy server
    URL = "https://s28.q4cdn.com/392171258/files/doc_downloads/test.pdf"  # Example PDF file

    # Send the request
    send_request(HOST, PORT, URL)
