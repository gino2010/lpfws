#!/usr/bin/env python
# -*- coding:utf-8 -*-
# python ./fws.pyc >/dev/null 2>&1 &
# netstat -lptun | grep 61980
import BaseHTTPServer
import ConfigParser
from SocketServer import ThreadingMixIn
import logging
import threading
import time
import requests
from daemon import runner

__author__ = 'gino'

HOST = ''
PORT = 0
LOGIN_PARAMS = {}
MAIN_URL = ''
MAIN_SEC = 0.5
ACL = ()
REPEAT = True
# For testing
DATA = ''


# Multithreading
class ThreadedHTTPServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
    pass


# Handler
class MyHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        """Respond to a GET request."""
        global DATA, ACL
        if self.client_address[0] in ACL:
            self.send_response(200)
            self.send_header("Content-Type", "text/html;charset=GBK")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            self.wfile.write(time.asctime())
            self.wfile.write(DATA.encode('GBK'))
        else:
            # self.send_response(404)
            print(self.client_address)
            logging.basicConfig(filename='deny.log', format='%(asctime)s - %(levelname)s - %(message)s')
            logging.warning('%s is denied' % self.client_address[0])

        message = threading.currentThread().getName()
        print(message)


def get_data_from_main():
    global MAIN_URL, LOGIN_PARAMS, MAIN_SEC, DATA, REPEAT
    req = requests.get(MAIN_URL, params=LOGIN_PARAMS)
    DATA = req.text
    if REPEAT:
        # print(time.asctime())
        threading.Timer(MAIN_SEC, get_data_from_main).start()


# initial server config parameter
def init_config():
    global HOST, PORT, LOGIN_PARAMS, MAIN_URL, MAIN_SEC, ACL
    config = ConfigParser.ConfigParser()
    config.read('/home/gino/Workspace/lpfws/config.ini')

    try:
        # Server config
        HOST = config.get('Server', 'HOST')
        PORT = int(config.get('Server', 'PORT'))

        # MAIN config
        MAIN_URL = config.get('MAIN', 'URL')
        LOGIN_PARAMS['username'] = config.get('MAIN', 'USERNAME')
        LOGIN_PARAMS['password'] = config.get('MAIN', 'PASSWORD')
        MAIN_SEC = float(config.get('MAIN', 'SEC'))

        # ACL config
        ACL = tuple(config.get('ACL', 'WLIST').split(','))
    except Exception as e:
        print(e.message)


class App():
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/tty'
        self.stderr_path = '/dev/tty'
        self.pidfile_path = '/tmp/testdaemon.pid'
        self.pidfile_timeout = 5

    def run(self):
        # initial server
        init_config()
        # This function will start a new thread via Timer module
        get_data_from_main()

        # Start a http server
        MyHandler.server_version = 'Light Forwarding Server/1.0'
        MyHandler.sys_version = ''
        httpd = ThreadedHTTPServer((HOST, PORT), MyHandler)
        print time.asctime(), "Server Starts - %s:%s" % (HOST, PORT)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        httpd.server_close()
        print time.asctime(), "Server Stops - %s:%s" % (HOST, PORT)


if __name__ == '__main__':
    app = App()
    logger = logging.getLogger("DaemonLog")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler = logging.FileHandler("/home/gino/Workspace/lpfws/testdaemon.log")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    daemon_runner = runner.DaemonRunner(app)
    # This ensures that the logger file handle does not get closed during daemonization
    daemon_runner.daemon_context.files_preserve = [handler.stream]
    daemon_runner.do_action()