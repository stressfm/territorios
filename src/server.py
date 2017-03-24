#!/usr/bin/env python
"""
TODO: Standardize response messages
{
    "clients": [{"stream": True|False, "name": "montemor|porto|lisboa|monitor",
          "ip": "111.111.11.11", "port": 8554}],
    "message": "some string",
    "label": "some string"
}
"""

from flask import Flask
from flask_uwsgi_websocket import GeventWebSocket, GeventWebSocketClient
import socket
from gevent import subprocess
import time
import os
import json

import logging

from utils import config_liq, check_rtsp_port, sanitize_to_json, get_local_ip


CONFIG = {"client_keys": [
                {"name": "porto", "key": "key1"},
                {"name": "montemor", "key": "key2"},
                {"name": "lisboa", "key": "key3"},
                {"name": "marte", "key": "key666"}
            ],
            "monitor_key": {"name": "monitor", "key": "monitorkey"}
         }
CLIENT_CMD = os.path.dirname(os.path.abspath(__file__)) + "/client.py"

LOGGER_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)
logging.basicConfig(
    format=LOGGER_FORMAT,
    level=logging.DEBUG)

if "MATRIZ_CONFIG_FILE" in os.environ:
    config_file = os.environ['MATRIZ_CONFIG_FILE']
else:
    config_file = 'clients.json'

if os.path.exists(config_file):
    cfg = open(config_file, 'r')
    config = json.load(cfg)
    CONFIG.update(config)
    cfg.close()
else:
    logging.debug("No configuration file found")

config = CONFIG

try:
    client_keys = [client["key"] for client in config['client_keys']]
    monitor_key = config['monitor_key']["key"]
except:
    logging.error("[QUIT] Bad configuration file: {}".format(config_file))
    exit(1)

try:
    connections = config["connections"]
except KeyError:
    pass

clients = {}
monitor = False
clients_for_web = {
    "lisboa": False,
    "porto": False,
    "montemor": False,
    "refresh": False,
    "restart": False
}

app = Flask(__name__)
websocket = GeventWebSocket(app)


def get_clients(web=False, rliq=False, refresh=False):

    if web:
        cl_w = {'restart': rliq, "refresh": refresh}
        for c in clients:
            clients_for_web[clients[c].name] = clients[c].stream
            cl_w[clients[c].name] = clients[c].stream
        for k, v in clients_for_web.iteritems():
            if k not in cl_w:
                cl_w[k] = False
        return cl_w
    else:
        cl = [{"ip": clients[c].ip, "stream": clients[c].stream,
               "name": clients[c].name, "port": clients[c].port} for c in client_keys if c in clients]
    return c


class Client(object):

    webclients = []
    local_clients = {}
    remote_clients = {}
    ports = [8552 + i for i in range(0, 20, 2)]
    local_processes = {}

    def __init__(self, ws=None, name="matriz", stream=False, port=8554, key=None):
        self.ws = ws
        self.stream = stream
        self.ip = None
        self.key = key
        self.name = name
        self.registered = False
        self.port = port
        self.connected = False

        if isinstance(ws, GeventWebSocketClient):
            self.ip = ws.environ['REMOTE_ADDR']
            self.ws_id = ws.id

    def register(self):
        restart_liquidsoap = False
        stream = False
        if self.key in client_keys:
            # logging.debug("checking port")
            connected, message = check_rtsp_port(address=self.ip, port=self.port)
            if connected:
                # logging.debug("stream is True")
                self.stream = True
            self.connected = True
            logging.debug("[Register {}]".format(self.name))
            self.registered = True
            clients[self.key] = self

        elif self.key == monitor_key:
            global monitor
            monitor = self
            self.name = "monitor"
            c = get_clients()
            if not c[1]:
                self.monitor(
                    {"status": "ok", "message": "No clients connected"})
            else:
                self.monitor({
                    "status": "ok",
                    "message": "\n".join(["[{}] connected with IP {}".format(t["name"], t["ip"])
                       for t in c[0]])})
        elif self.name == "webclient":
            self.webclients += [self]
            self.web = True
            cl = get_clients(web=True, rliq=restart_liquidsoap)
            logging.debug("For WEBCLIENT: %s" % (cl, ))
            self.ws.send(json.dumps(cl))

        else:
            self.deregister()

    def deregister(self):
        if self.name == "monitor":
            global monitor
            monitor = False
        elif self.registered:
            del clients[self.key]
            clients_for_web[self.name] = False
            logging.debug("[%s] DeRegistered" % (self.name))
        self.ws.close()
        self.monitor(
            {"status": "ok", "message": "[%s] disconnected" %
                    (self.name), "clients": get_clients()})
        msg = "[%s] disconnected from config server" % self.name
        logging.info("[%s] disconnected" % (self.name))
        logging.info("clients: %s" % json.dumps(get_clients()))

    def monitor(self, m):
        if not isinstance(monitor, Client):
            logging.debug("No monitor to send message")
            return False
        info = "Connected clients: %d" % (len(clients) - 1)
        message = json.dumps({"message": m["message"],
                              "info": info,
                              "clients": get_clients()})
        monitor.ws.send(message)

    def broadcast(self, msg, web=True, rliq=False):
        msg.update({"name": self.name,
                    "clients": get_clients()})
        msgj = json.dumps(msg)
        for c in client_keys:
            if c in clients and c != self.key:
                clients[c].ws.send(msgj)

        if web:
            if "refresh" in msg:
                refresh = True
            else:
                refresh = False

            webcl = json.dumps(
                get_clients(web=True, rliq=rliq, refresh=refresh))
            logging.debug("Web Message: %s" % (webcl,))
            for wc in self.webclients:
                wc.ws.send(webcl)
            return True

        self.monitor(msg)


@websocket.route('/config')
def socket_ws(ws):
    client_ip = ws.environ['REMOTE_ADDR']
    host_ip = ws.environ["HTTP_HOST"].split(":")[0]
    logging.debug("Connection started for ip: {}".format(client_ip))
    while ws.connected is True:
        response = ws.receive()
        # Message comes escaped
        try:
            msg = sanitize_to_json(response)
            #logging.debug("Sanitized message: {}".format(msg))
        except:
            msg = {}
        if msg:
            logging.debug("Message from {} is: {}".format(client_ip, msg))
        if "register" in msg and "name" in msg and "key" in msg and msg["name"]:
            client = Client(ws=ws, name=msg["name"], key=msg["key"], port=msg["port"])
            Client.remote_clients[client.name] = client
            logging.debug("Registering client named '{}' with ip '{}'".format(client.name, client_ip))
            client.register()
            if not(client.name.endswith("-local")):
                logging.debug("'{}' is not local; Client.local_clients: {}:".format(
                    client.name, Client.local_clients))
                if client.name not in Client.local_clients:
                    Client.local_clients[client.name] = Client.ports.pop()
                    logging.debug("Starting new local client for {}".format(client.name))
                else:
                    Client.local_processes[client.name].terminate()
                    logging.info("killed old local client for {}. Starting a new one".format(client.name))
                logging.info("Launching local client for {}".format(client.name))
                cmd = "{} -d -n {}-local -p {} -r {} -u {}".format(CLIENT_CMD, client.name, Client.local_clients[client.name], client.ip, "ws://{}:8080/config".format("127.0.0.1")).split(" ")
                logging.info("COMMAND IS: {}".format(cmd))
                Client.local_processes[client.name] = subprocess.Popen(cmd)
                time.sleep(1)
                msg.update({"clients": [{"ip": host_ip, "name": "{}-local".format(client.name), "stream": client.stream, "port": Client.local_clients[client.name]}]})
                logging.info("Reply to remote client {}: {}".format(client_ip, json.dumps(msg)))
                client.ws.send(json.dumps(msg))
            else:
                logging.info("Received connection from local client {}".format(client.name))


if __name__ == "__main__":

    app.run(
        debug=False,
        http="0.0.0.0:8080",
        gevent=100
    )

