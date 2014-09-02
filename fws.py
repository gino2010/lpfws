#!/usr/bin/env python
# -*- coding:utf-8 -*-
import ConfigParser
import logging
import logging.handlers
import threading
import time
import sys
import urlparse

from gevent.pywsgi import WSGIServer
import requests

from daemon import Daemon


__author__ = 'gino'

# Put data in memory
DATA = ''
# Debug flag
DEBUG = False


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
            self.auth = dict()
            self.auth['username'] = self._config.get('Server', 'USERNAME')
            self.auth['password'] = self._config.get('Server', 'PASSWORD')

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
                self.auth['username'] = self._config.get('Server', 'USERNAME')
                self.auth['password'] = self._config.get('Server', 'PASSWORD')
            except Exception as e:
                if DEBUG:
                    print('Reload configuration failure: %s' % e.message)
                run_logger.error('Reload configuration failure!')
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
        self._remote_url = ct.remote_url
        self._stop_flag = False

    def run(self):
        global DATA
        while not self._stop_flag:
            try:
                req = requests.get(self._remote_url, params=self._lp, timeout=0.3)
                DATA = req.text.encode('GBK')
                run_logger.info('Request boce server: %s' % self._remote_url[0:10])
            except Exception:
                run_logger.warning('Request timeout')
            if DEBUG:
                print(time.asctime())
            time.sleep(self._remote_sec)

    def stop(self):
        self._stop_flag = True


class ServerDaemon(Daemon):
    def __init__(self, pid):
        Daemon.__init__(self, pid)
        self._ct = ConfigThread()
        self._rt = RequestThread(self._ct)

    def data(self, environ, start_response):
        global DATA
        # parse parameters from GET request
        auth = urlparse.parse_qs(environ['QUERY_STRING'])
        for key in auth.keys():
            auth[key] = auth[key][0]

        # and environ['REMOTE_ADDR'] in self._ct.wacl
        if cmp(self._ct.auth, auth) == 0 and environ['REMOTE_ADDR'] not in self._ct.bacl:
            status = '200 OK'
            headers = [
                ('Content-Type', 'text/html;charset=GBK'),
                ('Server:', 'Light Forwarding Server/1.0 beta')
            ]

            start_response(status, headers)
            run_logger.warning('from ip: %s request' % environ['REMOTE_ADDR'])
            return [DATA]
        else:
            run_logger.warning('%s is denied' % environ['REMOTE_ADDR'])
            start_response('404 Not Found', [('Content-Type', 'text/html')])
            return []

    def run(self):
        # initialize server configuration
        self._ct.start()
        run_logger.info('initial config success')

        # start to request remote server for getting forwarding data
        self._rt.start()

        # Start http server
        httpd = WSGIServer((self._ct.host, self._ct.port), self.data)
        try:
            httpd.serve_forever()
            run_logger.info("Server Started - %s:%s" % (self._ct.host, self._ct.port))
        except KeyboardInterrupt:
            pass

        # Stop http server only in debug mode
        httpd.stop()
        self._rt.stop()
        self._ct.stop()
        run_logger.info("Server Stopped - %s:%s" % (self._ct.host, self._ct.host))


if __name__ == '__main__':
    # only init LOG and PID
    oc = ConfigParser.ConfigParser()
    oc.read('config.ini')
    LOG = oc.get('LOG', 'PATH')
    PID = oc.get('PID', 'PATH')
    DEBUG = bool(oc.get('Server', 'DEBUG') == '1')

    # configure logging, handler request package logging
    run_logger = logging.getLogger("my.server.forward")
    run_logger.setLevel(logging.INFO)

    # rotate file every midnight
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

        # perfect ACL function
        # request session
        # concurrent control