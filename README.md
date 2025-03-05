# CPSC-441-A2
This project implements a simple HTTP proxy server in Python. When the proxy intercepts requests for images, it discards the original image and instead serves a random meme image from a specified folder. In addition, the proxy displays a custom Easter egg page when a specific URL (e.g., http://google.ca) is requested.

Configure Browser for testing 
Since the proxy server listens on 127.0.0.1:8080 by default, you need to configure your browser to use this proxy.

1. Firefox
1. Open Options.
3. Scroll down to Network Settings and click Settings....
4. Select Manual proxy configuration.
5. Set HTTP Proxy to 127.0.0.1 and Port to 8080.
6. Check "Use this proxy server for all protocols."
7. Click OK.

Running Server 
1. Start the Proxy Server: Run the Python script:
python  MohammedHossain_Proxy_Server.py


2. Test the Proxy:
Visit image endpoints (e.g., http://httpbin.org/image, http://httpbin.org/image/jpeg, http://httpbin.org/image/png) in your browser.
Visit http://google.ca to see the custom Easter egg page.
Non-image requests will be forwarded normally.
