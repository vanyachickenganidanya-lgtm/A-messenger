# web_server.py
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import json

PORT = int(os.getenv("PORT", 10000))

class PortHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        try:
            with open("/tmp/bore_port", "r") as f:
                bore_port = f.read().strip()
        except:
            bore_port = "0"
        response = {"port": bore_port, "host": "bore.pub"}
        self.wfile.write(json.dumps(response).encode('utf-8'))

if __name__ == "__main__":
    server = HTTPServer(('0.0.0.0', PORT), PortHandler)
    print(f"Web server started on port {PORT}")
    server.serve_forever()
