#!/usr/bin/env python
# -*- coding:utf-8 -*-
import BaseHTTPServer
import ConfigParser
from SocketServer import ThreadingMixIn, BaseRequestHandler
import logging
import logging.handlers
import threading
import time
import sys

import requests

from daemon import Daemon


__author__ = 'gino'

# HOST = ''
# PORT = 0
# LOGIN_PARAMS = {}
# REMOTE_URL = ''
# REMOTE_SEC = 0.5
# WACL = ()
# BACL = ()
# For testing
DATA = ''
DEBUG = False


# Multithreading
class ThreadedHTTPServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
    pass


# Handler
class ForwardHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def __init__(self, ct, *args):
        self.wacl = ct.wacl
        self.bacl = ct.bacl
        BaseRequestHandler.__init__(self, *args)

    def do_GET(self):
        """Respond to a GET request."""
        global DATA
        if self.client_address[0] in self.wacl and self.client_address[0] not in self.bacl:
            self.send_response(200)
            self.send_header("Content-Type", "text/html;charset=GBK")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            self.wfile.write(DATA.encode('GBK'))
            run_logger.warning('from ip: %s request' % self.client_address[0])
        else:
            run_logger.warning('%s is denied' % self.client_address[0])


def handleRequestsUsing(ct):
    return lambda *args: ForwardHandler(ct, *args)


# initial server config parameter
class ConfigThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self._stop_flag = False
        self._config = ConfigParser.ConfigParser()
        self._config.read('config.ini')
        try:
            # Server config
            self.host = self._config.get('Server', 'HOST')
            self.port = int(self._config.get('Server', 'PORT'))

            # REMOTE config
            self.remote_url = self._config.get('Remote', 'URL')
            self.lp = dict()
            self.lp['username'] = self._config.get('Remote', 'USERNAME')
            self.lp['password'] = self._config.get('Remote', 'PASSWORD')
            self.remote_sec = float(self._config.get('Remote', 'SEC'))

            # ACL config
            self.wacl = tuple(self._config.get('ACL', 'WLIST').split(','))
            self.bacl = tuple(self._config.get('ACL', 'BLIST').split(','))
        except Exception as e:
            if DEBUG:
                print('Initialize configuration failure: %s' % e.message)
            run_logger.error('Initialize configuration failure!')
            run_logger.error(e.message)
            sys.exit(0)

    def run(self):
        while not self._stop_flag:
            try:
                self._config.read('config.ini')
                self.wacl = tuple(self._config.get('ACL', 'WLIST').split(','))
                self.bacl = tuple(self._config.get('ACL', 'BLIST').split(','))
            except Exception as e:
                if DEBUG:
                    print('Reload acl failure: %s' % e.message)
                run_logger.error('Reload acl failure!')
                run_logger.error(e.message)
            time.sleep(10)

    def stop(self):
        self._stop_flag = True


# Request thread to get data from remote server
class RequestThread(threading.Thread):
    def __init__(self, ct):
        threading.Thread.__init__(self)
        self._remote_url = ct.remote_url
        self._lp = ct.lp
        self._remote_sec = ct.remote_sec
        self._stop_flag = False

    def run(self):
        global DATA
        while not self._stop_flag:
            try:
                req = requests.get(self._remote_url, params=self._lp, timeout=0.3)
                DATA = req.text
            except Exception:
                logging.warning('request timeout')
            if DEBUG:
                print(time.asctime())
            time.sleep(self._remote_sec)

    def stop(self):
        self._stop_flag = True


class ServerDaemon(Daemon):
    def run(self):
        # Do stuff
        # initialize server configuration
        # init_config()
        ct = ConfigThread()
        ct.start()
        run_logger.info('initial config success')

        # start to request remote server for getting forwarding data
        rt = RequestThread(ct)
        rt.start()

        # Start http server
        ForwardHandler.server_version = 'Light Forwarding Server/1.0'
        ForwardHandler.sys_version = ''
        fh = handleRequestsUsing(ct)
        httpd = ThreadedHTTPServer((ct.host, ct.port), fh)
        run_logger.info("Server Starts - %s:%s" % (ct.host, ct.port))
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass

        # Stop http server only in debug mode
        httpd.server_close()
        rt.stop()
        ct.stop()
        run_logger.info("Server Stops - %s:%s" % (ct.host, ct.host))


if __name__ == '__main__':
    # only init LOG and PID
    oc = ConfigParser.ConfigParser()
    oc.read('config.ini')
    LOG = oc.get('LOG', 'PATH')
    PID = oc.get('PID', 'PATH')
    DEBUG = bool(oc.get('Server', 'DEBUG') == '1')

    # configure logging, handler request package logging
    run_logger = logging.getLogger("requests.packages.urllib3")
    run_logger.setLevel(logging.INFO)

    # rorate file by midnight
    handler = logging.handlers.TimedRotatingFileHandler(LOG, when="midnight", backupCount=5)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    run_logger.addHandler(handler)

    # start server in daemon mode
    sd = ServerDaemon(PID)
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            if DEBUG:
                sd.run()
            else:
                sd.start()
        elif 'stop' == sys.argv[1]:
            sd.stop()
        elif 'restart' == sys.argv[1]:
            sd.restart()
        else:
            print ('Unknown command')
    else:
        print('Usage: start/stop/restart')

        # user auth
        #auto acl