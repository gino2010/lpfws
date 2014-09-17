Lightweight Forwarding Web Server
=====
* Using Python language
* Request data from a web server and save data in one specific form
* Start a base http server to forwarding saved data to other users
* The purpose is for requesting diversion and data sharing

Features
---------
1. Base on gevent pywsgi WSGIServer, support user authentication
2. Use requests lib to get data
3. Access control list: white and black, automatic reload in absolute thread
4. Configuration in config.ini
5. Logging, rotate file every midnight
6. Daemonizer base on https://github.com/serverdensity/python-daemon
7. analyze.py is analysis tools for this web server

License
---------
GPL V2
