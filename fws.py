# -*- coding:utf-8 -*-
# python ./fws.pyc >/dev/null 2>&1 &
# netstat -lptun | grep 8000
import BaseHTTPServer
import ConfigParser
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
# For testing
DATA = ''


class MyHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    # def do_HEAD(self):
    # self.send_response(200)
    #     self.send_header("Content-type", "text/html;charset=GBK")
    #     self.send_header("Server", "ForwardingServer/1.0")
    #     self.end_headers()

    def do_GET(self):
        """Respond to a GET request."""
        global DATA, ACL
        if self.client_address[0] in ACL:
            self.send_response(200)
            self.send_header("Content-Type", "text/html;charset=GBK")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            self.wfile.write(DATA.encode('GBK'))
            # else:
            #     self.send_response(404)


def get_data_from_MAIN():
    global MAIN_URL, LOGIN_PARAMS, MAIN_SEC, DATA
    req = requests.get(MAIN_URL, params=LOGIN_PARAMS)
    DATA = req.text
    # print(time.asctime())
    threading.Timer(MAIN_SEC, get_data_from_MAIN).start()


# initial server config parameter
def init_config():
    global HOST, PORT, LOGIN_PARAMS, MAIN_URL, MAIN_SEC, ACL
    config = ConfigParser.ConfigParser()
    config.read('./config.ini')

    # Server config
    HOST = config.get('Server', 'HOST')
    PORT = int(config.get('Server', 'PORT'))

    #MAIN config
    MAIN_URL = config.get('MAIN', 'URL')
    LOGIN_PARAMS['username'] = config.get('MAIN', 'USERNAME')
    LOGIN_PARAMS['password'] = config.get('MAIN', 'PASSWORD')
    MAIN_SEC = float(config.get('MAIN', 'SEC'))

    #ACL config
    ACL = tuple(config.get('ACL', 'WLIST').split(','))


if __name__ == '__main__':
    # initial server
    init_config()
    #This function will start a new thread via Timer module
    get_data_from_MAIN()

    #Start a http server
    MyHandler.server_version = 'Light Forwarding Server/1.0'
    MyHandler.sys_version = ''
    httpd = BaseHTTPServer.HTTPServer((HOST, PORT), MyHandler)
    print time.asctime(), "Server Starts - %s:%s" % (HOST, PORT)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print time.asctime(), "Server Stops - %s:%s" % (HOST, PORT)