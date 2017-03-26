#!/usr/bin/env python
"""
TODO: Standardize response messages
"server": {
    "start": {
       "receiver": {"ip": "111.111.111.1", "port":8554, "name": "name of emitter" },
       "emitter": {"port": 8554},
       "audiotest": {}
    }
    "stop": {
       "emitter": {},
       "receiver": {"name": "somename"},
       "audiotest":{},
    }
    "status": {}
}
"client": {
    "register": "",
    "ports": [],
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


CONFIG = {
    "client_keys": [
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
        cl = [
            {
                "ip": clients[c].ip,
                "stream": clients[c].stream,
                "name": clients[c].name,
                "port": clients[c].port
            } for c in client_keys if c in clients
        ]
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
        if ws.environ['HTTP_HOST'].split(":")[0] == "127.0.0.1":
            self.local = True
        else:
            self.local = False
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
            logging.debug("For WEBCLIENT: {}".format(cl))
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
            logging.debug("[{}] DeRegistered".format(self.name))
        self.ws.close()
        self.monitor({
            "status": "ok",
            "message": "[{}] disconnected".format(self.name),
            "clients": get_clients()
        })
        msg = "[{}] disconnected from config server".format(self.name)
        logging.info("[{}] disconnected".format(self.name))
        logging.info("clients: {}".format(json.dumps(get_clients())))

    def monitor(self, m):
        if not isinstance(monitor, Client):
            logging.debug("No monitor to send message")
            return False
        info = "Connected clients: {}".format(len(clients) - 1)
        message = json.dumps({
            "message": m["message"],
            "info": info,
            "clients": get_clients()
        })
        monitor.ws.send(message)

    def broadcast(self, msg, web=True, rliq=False):
        msg.update({
            "name": self.name,
            "clients": get_clients()
        })
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
                get_clients(web=True, rliq=rliq, refresh=refresh)
            )
            logging.debug("Web Message: {}".format(webcl))
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
            if not client.local:
                logging.debug("'{}' is not local; Client.local_clients: {}:".format(
                    client.name, Client.local_clients
                ))

                if client.name not in Client.local_clients:
                    Client.local_clients[client.name] = Client.ports.pop()
                else:
                    Client.local_processes[client.name].terminate()
                    logging.info("killed old local client for {}. Starting a new one".format(client.name))
                logging.info("Launching local client for {}".format(client.name))
                cmd = "{} -d -L -n {} -p {} -r {} -R {} -u {}".format(CLIENT_CMD, client.name, Client.local_clients[client.name], client.ip, client.port, "ws://{}:8080/config".format("127.0.0.1")).split(" ")
                logging.info("COMMAND IS: {}".format(cmd))
                Client.local_processes[client.name] = subprocess.Popen(cmd)
                counter = 0
                while not check_rtsp_port(address="127.0.0.1", port=Client.local_clients[client.name])[0]:
                    counter += 1
                    time.sleep(.5)
                    if counter > 5:
                        logging.debug("Could not connect to 127.0.0.1 at port {}, client '{}' might not connect to rtsp stream".format(Client.local_clients[client.name], client.name))
                        break
                logging.debug("Ticked {} times until stream up".format(counter))
                # Deprecation: adding -local to use old matriz clients
                msg.update({"clients": [{"ip": host_ip, "name": "{}-local".format(client.name), "stream": client.stream, "port": Client.local_clients[client.name]}]})
                logging.info("Reply to remote client {}-local: {}".format(client_ip, json.dumps(msg)))
                client.ws.send(json.dumps(msg))
            else:
                logging.info("Received connection from local client {}".format(client.name))
    Client.local_processes[client.name].terminate()
    Client.ports += [Client.local_clients[client.name]]

if __name__ == "__main__":
    # This won't work with supervisor, spawns a shell and child processes will not be
    # manageable by supervisor daemon
    # Only to be used when testing
    app.run(
        host="0.0.0.0",
        port=8080,
        master=True,
        gevent=100
    )
