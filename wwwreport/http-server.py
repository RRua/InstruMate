import argparse
import http.server
import os
from urllib.parse import unquote

STATIC_FOLDER = ""
DYNAMIC_FOLDER = ""


class DualFolderHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        global STATIC_FOLDER
        global DYNAMIC_FOLDER
        path = unquote(path)
        for folder in [STATIC_FOLDER, DYNAMIC_FOLDER]:
            potential_path = os.path.join(folder, path.lstrip('/'))
            if os.path.exists(potential_path):
                return potential_path
        return super().translate_path(path)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()


def main(static_folder, dynamic_folder):
    global STATIC_FOLDER
    global DYNAMIC_FOLDER
    STATIC_FOLDER = static_folder
    DYNAMIC_FOLDER = dynamic_folder
    server_address = ('', 8000)
    httpd = http.server.HTTPServer(server_address, DualFolderHTTPRequestHandler)
    print(f"Serving HTTP on port 8000...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down http server.")
        httpd.socket.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process two arguments.')
    parser.add_argument('static_folder', type=str, help='The static folder')
    parser.add_argument('dynamic_folder', type=str, help='The dynamic data folder (project folder)')
    opts = parser.parse_args()
    main(opts.static_folder, opts.dynamic_folder)