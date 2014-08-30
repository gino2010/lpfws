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
            my_logger.warning('from ip: %s request' % self.client_address[0])
        else:
            # self.send_response(404)
            # print(self.client_address)
            my_logger.warning('%s is denied' % self.client_address[0])

            # message = threading.currentThread().getName()
            # print(message)


def get_data_from_main():
    global MAIN_URL, LOGIN_PARAMS, MAIN_SEC, DATA, REPEAT
    try:
        req = requests.get(MAIN_URL, params=LOGIN_PARAMS)
        DATA = req.text
    except Exception:
        print('timeout')
    print(time.asctime())
    threading.Timer(MAIN_SEC, get_data_from_main).start()


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
        my_logger.warning(e.message)


class MyThread(threading.Thread):
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
                print('timeout')
            print(time.asctime())
            time.sleep(self._main_sec)

    def stop(self):
        self._stop_flag = True


if __name__ == '__main__':
    # initial server
    init_config()
    # This function will start a new thread via Timer module
    # get_data_from_main()
    thread = MyThread(MAIN_URL, LOGIN_PARAMS, MAIN_SEC)
    thread.start()

    # logging.basicConfig(filename='fws%s.log' % str(datetime.date.today()), format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
    my_logger = logging.getLogger("requests.packages.urllib3")
    my_logger.setLevel(logging.INFO)
    handler = logging.handlers.TimedRotatingFileHandler('run.log', when="midnight", backupCount=5)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    my_logger.addHandler(handler)
    my_logger.info('initial config success')

    # Start a http server
    MyHandler.server_version = 'Light Forwarding Server/1.0'
    MyHandler.sys_version = ''
    httpd = ThreadedHTTPServer((HOST, PORT), MyHandler)
    my_logger.info("Server Starts - %s:%s" % (HOST, PORT))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    thread.stop()
    my_logger.info("Server Stops - %s:%s" % (HOST, PORT))