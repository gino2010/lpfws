#!/usr/bin/env python
# -*- coding:utf-8 -*-
# python ./fws.pyc >/dev/null 2>&1 &
# netstat -lptun | grep 61980
import BaseHTTPServer
import ConfigParser
from SocketServer import ThreadingMixIn
import logging
import logging.handlers
import threading
import time

import requests
import sys


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
DEBUG = True


# Multithreading
class ThreadedHTTPServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
    pass


# Handler
class ForwardHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        """Respond to a GET request."""
        global DATA, ACL
        if self.client_address[0] in ACL:
            self.send_response(200)
            self.send_header("Content-Type", "text/html;charset=GBK")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            self.wfile.write(DATA.encode('GBK'))
            run_logger.warning('from ip: %s request' % self.client_address[0])
        else:
            run_logger.warning('%s is denied' % self.client_address[0])


# initial server config parameter
def init_config():
    global HOST, PORT, LOGIN_PARAMS, MAIN_URL, MAIN_SEC, ACL
    config = ConfigParser.ConfigParser()
    config.read('config.ini')

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
        run_logger.error('Initialize configuration failure!')
        run_logger.error(e.message)
        sys.exit(0)


# Request thread to get data from remote server
class RequestThread(threading.Thread):
    def __init__(self, main_url, login_params, main_sec):
        threading.Thread.__init__(self)
        self._main_url = main_url
        self._login_params = login_params
        self._main_sec = main_sec
        self._stop_flag = False

    def run(self):
        global DATA
        while not self._stop_flag:
            try:
                req = requests.get(self._main_url, params=self._login_params, timeout=0.3)
                DATA = req.text
            except Exception:
                logging.warning('request timeout')
            if DEBUG:
                print(time.asctime())
            time.sleep(self._main_sec)

    def stop(self):
        self._stop_flag = True


if __name__ == '__main__':
    # configure logging, handler request package logging
    run_logger = logging.getLogger("requests.packages.urllib3")
    run_logger.setLevel(logging.INFO)
    # rorate file by midnight
    handler = logging.handlers.TimedRotatingFileHandler('run.log', when="midnight", backupCount=5)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    run_logger.addHandler(handler)

    # initialize server configuration
    init_config()
    run_logger.info('initial config success')

    # start to request remote server for getting forwarding data
    thread = RequestThread(MAIN_URL, LOGIN_PARAMS, MAIN_SEC)
    thread.start()

    # Start http server
    ForwardHandler.server_version = 'Light Forwarding Server/1.0'
    ForwardHandler.sys_version = ''
    httpd = ThreadedHTTPServer((HOST, PORT), ForwardHandler)
    run_logger.info("Server Starts - %s:%s" % (HOST, PORT))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

    # Stop http server
    httpd.server_close()
    thread.stop()
    run_logger.info("Server Stops - %s:%s" % (HOST, PORT))