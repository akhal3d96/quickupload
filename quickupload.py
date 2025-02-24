#!/usr/bin/env python3

from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import re
import argparse
import socket

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Upload</title>
    <style>
        body {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            height: 100vh;
            text-align: center;
            font-family: Arial, sans-serif;
        }
        button {
            width: 300px;
            height: 60px;
            font-size: 18px;
            background-color: blue;
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }
        button.uploading {
            background-color: green;
        }
        progress {
            width: 100%;
            margin-top: 10px;
        }
        footer {
            position: absolute;
            bottom: 10px;
            font-size: 14px;
        }
        footer a {
            color: #007bff;
            text-decoration: none;
        }
        footer a:hover {
            text-decoration: underline;
        }
    </style>
    <script>
        function readErrorMessage(errorMessage) {
            err = JSON.parse(errorMessage)
            return err.message
        }

        function uploadFile() {
            const fileInput = document.getElementById('file');
            const file = fileInput.files[0];
            const button = document.getElementById('uploadButton');
            if (!file) {
                alert('No file selected');
                return;
            }

            button.classList.add('uploading');
            button.innerText = "Uploading... 0%";

            const formData = new FormData();
            formData.append('file', file);

            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/', true);

            let startTime = Date.now();

            xhr.upload.addEventListener('progress', function(event) {
                if (event.lengthComputable) {
                    const percentComplete = ((event.loaded / event.total) * 100).toFixed(2);
                    document.getElementById('progressBar').value = percentComplete;
                    
                    const elapsedTime = (Date.now() - startTime) / 1000; // seconds
                    let speedText = "Speed: 0 MiB/s";
                    if (elapsedTime > 0) {
                        const speed = (event.loaded / (1024 * 1024)) / elapsedTime; // MiB/s
                        speedText = `Speed: ${speed.toFixed(2)} MiB/s`;
                    }
                    document.getElementById('speedText').innerText = speedText;

                    button.innerText = `Uploading... ${percentComplete}%`;
                }
            });

            xhr.onerror = (err) => {
                alert(`Error occurred during file upload: ${readErrorMessage(err.currentTarget.response)}.`);
                location.reload();
            };

            xhr.onload = (err) => {
                if (xhr.status === 200) {
                    alert('File uploaded successfully!');
                } else {
                    alert(`Error occurred during file upload: ${readErrorMessage(err.currentTarget.response)}.`);
                }
                location.reload();
            };

            xhr.send(formData);
        }
    </script>
</head>
<body>
    <h1>Upload File</h1>
    <form>
        <input type="file" id="file" name="file"><br>
        <progress id="progressBar" value="0" max="100"></progress><br>
        <span id="speedText">Speed: 0 MiB/s</span><br>
        <button type="button" id="uploadButton" onclick="uploadFile()">Upload</button>
    </form>

    <footer>
        Source code: <a href="https://github.com/akhal3d96/quickupload" target="_blank">github.com/akhal3d96/quickupload</a>
    </footer>
</body>
</html>
"""


class UploaderHTTPHander(BaseHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        if directory is None:
            directory = os.getcwd()
        else:
            os.makedirs(directory, exist_ok=True)

        self.directory = os.fspath(directory)
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_TEMPLATE.encode())

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])

        deductable = 0
        while self.rfile.readable():
            line = self.rfile.readline()
            deductable += len(line)

            if line == b"\r\n":
                break
            elif line[: len("Content-Disposition")].decode() == "Content-Disposition":
                filename = re.search(r'filename="(.+)"', line.decode()).group(1)

        content_length -= deductable
        filepath = os.path.join(self.directory, filename)
        try:
            with open(filepath, "wb") as f:
                bytes_read = 0
                while bytes_read < content_length:
                    chunk_size = min(64 * 1024, content_length - bytes_read)
                    chunk = self.rfile.read(chunk_size)
                    # if chunk == b'':
                    #     break
                    bytes_read += f.write(chunk)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

        except Exception as e:
            self.send_response(500)  # Internal Server Error
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(f'{{"message": "Error uploading file: {e}"}}'.encode())


def get_interface_ip(family: socket.AddressFamily) -> str:
    host = "fd31:f903:5ab5:1::1" if family == socket.AF_INET6 else "10.253.155.219"

    with socket.socket(family, socket.SOCK_DGRAM) as s:
        try:
            s.connect((host, 58162))
        except OSError:
            return "::1" if family == socket.AF_INET6 else "127.0.0.1"

        return s.getsockname()[0]


def run(server_class=HTTPServer, handler_class=UploaderHTTPHander, host="", port=5000):
    server_address = (host, port)
    httpd = server_class(server_address, handler_class)
    external_ip = get_interface_ip(socket.AF_INET)
    print(f"Starting server on  http://{external_ip}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-p", "--port", help="the port the server listen on", type=int, default=5000
    )
    parser.add_argument("-a", "--host", help="host to bind on", default="0.0.0.0")
    parser.add_argument(
        "-d",
        "--directory",
        help="directory to save the uploaded files at",
        default=os.getcwd(),
    )
    # parser.add_argument("-b", "--basicauth", help="username:password to enable basic auth", default="") # TODO

    class ServerClass(HTTPServer):
        def finish_request(self, request, client_address):
            self.RequestHandlerClass(
                request, client_address, self, directory=args.directory
            )

    args = parser.parse_args()

    try:
        run(server_class=ServerClass, host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("shutdown")
