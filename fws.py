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
import sys
from daemon import Daemon

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
            self.wfile.write(DATA.encode('GBK'))
        else:
            # self.send_response(404)
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
    config.read('./config.ini')

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


class MyDaemon(Daemon):
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
    daemon = MyDaemon('/tmp/forwardserver.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)