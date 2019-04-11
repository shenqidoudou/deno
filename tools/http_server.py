#!/usr/bin/env python
# Copyright 2018-2019 the Deno authors. All rights reserved. MIT license.
# Many tests expect there to be an http server on port 4545 servering the deno
# root directory.
import os
import sys
from threading import Thread
import SimpleHTTPServer
import SocketServer
from util import root_path
from time import sleep

PORT = 4545
REDIRECT_PORT = 4546
ANOTHER_REDIRECT_PORT = 4547
DOUBLE_REDIRECTS_PORT = 4548


class ContentTypeHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_GET(self):
        if "multipart_form_data.txt" in self.path:
            self.protocol_version = 'HTTP/1.1'
            self.send_response(200, 'OK')
            self.send_header('Content-type',
                             'multipart/form-data;boundary=boundary')
            self.end_headers()
            self.wfile.write(
                bytes('Preamble\r\n'
                      '--boundary\t \r\n'
                      'Content-Disposition: form-data; name="field_1"\r\n'
                      '\r\n'
                      'value_1 \r\n'
                      '\r\n--boundary\r\n'
                      'Content-Disposition: form-data; name="field_2"; '
                      'filename="file.js"\r\n'
                      'Content-Type: text/javascript\r\n'
                      '\r\n'
                      'console.log("Hi")'
                      '\r\n--boundary--\r\n'
                      'Epilogue'))
            return
        return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        # Simple echo server for request reflection
        if "echo_server" in self.path:
            self.protocol_version = 'HTTP/1.1'
            self.send_response(200, 'OK')
            if self.headers.has_key('content-type'):
                self.send_header('content-type',
                                 self.headers.getheader('content-type'))
            self.end_headers()
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            self.wfile.write(bytes(data_string))
            return
        self.protocol_version = 'HTTP/1.1'
        self.send_response(501)
        self.send_header('content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(bytes('Server does not support this operation'))

    def guess_type(self, path):
        if ".t1." in path:
            return "text/typescript"
        if ".t2." in path:
            return "video/vnd.dlna.mpeg-tts"
        if ".t3." in path:
            return "video/mp2t"
        if ".t4." in path:
            return "application/x-typescript"
        if ".j1." in path:
            return "text/javascript"
        if ".j2." in path:
            return "application/ecmascript"
        if ".j3." in path:
            return "text/ecmascript"
        if ".j4." in path:
            return "application/x-javascript"
        if "form_urlencoded" in path:
            return "application/x-www-form-urlencoded"
        if "no_ext" in path:
            return "text/typescript"
        if "unknown_ext" in path:
            return "text/typescript"
        if "mismatch_ext" in path:
            return "text/javascript"
        return SimpleHTTPServer.SimpleHTTPRequestHandler.guess_type(self, path)


def server():
    os.chdir(root_path)  # Hopefully the main thread doesn't also chdir.
    Handler = ContentTypeHandler
    Handler.extensions_map.update({
        ".ts": "application/typescript",
        ".js": "application/javascript",
        ".json": "application/json",
    })
    SocketServer.TCPServer.allow_reuse_address = True
    s = SocketServer.TCPServer(("", PORT), Handler)
    print "Deno test server http://localhost:%d/" % PORT
    return s


def base_redirect_server(host_port, target_port, extra_path_segment=""):
    os.chdir(root_path)
    target_host = "http://localhost:%d" % target_port

    class RedirectHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(301)
            self.send_header('Location',
                             target_host + extra_path_segment + self.path)
            self.end_headers()

    Handler = RedirectHandler
    SocketServer.TCPServer.allow_reuse_address = True
    s = SocketServer.TCPServer(("", host_port), Handler)
    print "redirect server http://localhost:%d/ -> http://localhost:%d/" % (
        host_port, target_port)
    return s


# redirect server
def redirect_server():
    return base_redirect_server(REDIRECT_PORT, PORT)


# another redirect server pointing to the same port as the one above
# BUT with an extra subdir path
def another_redirect_server():
    return base_redirect_server(
        ANOTHER_REDIRECT_PORT, PORT, extra_path_segment="/tests/subdir")


# redirect server that points to another redirect server
def double_redirects_server():
    return base_redirect_server(DOUBLE_REDIRECTS_PORT, REDIRECT_PORT)


def spawn():
    # Main http server
    s = server()
    thread = Thread(target=s.serve_forever)
    thread.daemon = True
    thread.start()
    # Redirect server
    rs = redirect_server()
    r_thread = Thread(target=rs.serve_forever)
    r_thread.daemon = True
    r_thread.start()
    # Another redirect server
    ars = another_redirect_server()
    ar_thread = Thread(target=ars.serve_forever)
    ar_thread.daemon = True
    ar_thread.start()
    # Double redirects server
    drs = double_redirects_server()
    dr_thread = Thread(target=drs.serve_forever)
    dr_thread.daemon = True
    dr_thread.start()
    sleep(1)  # TODO I'm too lazy to figure out how to do this properly.
    return thread


def main():
    try:
        thread = spawn()
        while thread.is_alive():
            sleep(10)
    except KeyboardInterrupt:
        pass
    sys.exit(1)


if __name__ == '__main__':
    main()