#!/usr/bin/env python
from __future__ import print_function
import time
import random
import sys
import ssl
import os
import json
import argparse
import logging
import atexit
import signal
import threading
import time

import websocket
import miniupnpc

from time import strftime


import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst


from emitter import Emitter
from receiver import Receiver
from utils import check_rtsp_port
from jack_client import JackClient


BANNER = """
*************************************************************
                      Matriz - Cliente
*************************************************************
"""

SERVER_URL = "wss://matriz.stress.fm/config"

CONFIG = {
    "local": False,
    "python": True,
    "receive": True,
    "key": "key2",
    "name": "",
    "url": "ws://matriz.stress.fm/config",
    "port": 8554,
    "record": False,
    "client_pem": "",
    "client_crt": "",
    "ca_crt": "",
    "receive_from_ip": None,
    "receive_from_port": None,
}

LOGGER_FORMAT = '%(asctime)s - CLIENT - %(levelname)s - %(message)s'

logger = logging.getLogger(__name__)


def _create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('config_file',
                        type=str,
                        nargs="?",
                        default="client.json")
    parser.add_argument('-d',
                        '--debug',
                        action="store_true",
                        default=False)
    parser.add_argument('-L',
                        '--local',
                        action="store_true",
                        default=False)
    parser.add_argument('-T',
                        '--audio-test',
                        action="store_true",
                        default=False)
    parser.add_argument('-p',
                        '--port',
                        type=int)
    parser.add_argument('-n',
                        '--name',
                        type=str)
    parser.add_argument('-u',
                        '--url',
                        type=str)
    parser.add_argument('-r',
                        '--receive_from_ip',
                        type=str)
    parser.add_argument('-R',
                        '--receive_from_port',
                        type=int)
    parser.add_argument('-A',
                        '--alsa',
                        action="store_true",
                        default=False)
    return parser


def main(arguments=sys.argv[1:]):
    parser = _create_parser()
    args = parser.parse_args(arguments)
    if args.debug:
        logging.basicConfig(
            format=LOGGER_FORMAT,
            level=logging.DEBUG)
    else:
        # Log info and above to console
        logging.basicConfig(
            # format='%(levelname)s: %(message)s',
            format=LOGGER_FORMAT,
            level=logging.INFO
        )
    logging.info(BANNER)
    config_from_file = {}
    if not args.local:
        try:
            # Read config file
            with open("{}/{}".format(os.environ["HOME"],args.config_file)) as f:
                config_from_file = json.load(f)
                logging.debug(config_from_file)
                CONFIG.update(config_from_file)
        except:
            logging.info("file {} does not exist!\n".format(args.config_file))

    config = CONFIG


    logging.info("\n{} Program Started at: {}\n\n".format(
        "*"*20, strftime("%Y-%m-%d %H:%M:%S"), "*"*20))
    logging.debug("Options:")

    for key, value in (vars(args)).items():
        logging.debug("{0}: {1}".format(key, value))
        if key not in config_from_file:
            config[key] = value
    logging.debug(config)

    # Actually run the program
    matriz = Matriz(config=config)
    matriz()
    logging.info("\n{} Program Ended at: {}\n\n".format(
        "*"*20, strftime("%Y-%m-%d %H:%M:%S"), "*"*20))


class Matriz:

    emitter = False

    def __init__(self, config={}):
        logging.debug("{}".format(config))
        self.alsa = config["alsa"]
        self.config_server_url = config.get("url", "ws://matriz.stress.fm/config")
        self.local = config.get("local", False)
        self.mode = config.get("mode", "centralized")
        self.port = config.get("port", 8854)
        self.python = config.get("python", True)
        self.receive = config.get("receive", True)
        self.name = config.get("name", "matriz_client")
        self.key = config.get("key", "")
        self.record = config.get("record", False)
        self.upnp_client = miniupnpc.UPnP()
        self.connection_attempts = 0
        self.receive_from_ip = config.get("receive_from_ip", None)
        self.receive_from_port = config.get("receive_from_port", None)
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, self.cleanup)
        GObject.threads_init()
        Gst.init(None)

    def on_message(self, ws, message):
        try:
            message = json.loads(message)
            logging.debug("{}: Received message from server:".format(self.name))
            logging.debug(message)
        except:
            logging.debug("[Error] Couldn't read message: %s" % (message, ))
            return
        if not self.receive:
            return
        logging.debug("Running receivers: {}".format(Receiver.receivers))

        if self.mode != "centralized":
            # Check connected receivers and disconnect any that is not
            # on the client list obtained from server
            for client in message["clients"]:
                name = client["name"]
                if name in Receiver.receivers:
                    logging.debug("Receiver for {} already running".format(name))
                    continue
                else:
                    logging.debug("Starting receiver for {}\nwith client: {}".format(name, client))
                    client["name"] = self.name
                    client["alsa"] = self.alsa
                    receiver = Receiver(**client)
                    receiver()
        else:
            if not Receiver.receivers.get(self.name, None):
                logging.debug("Starting receiver from central server")
                client = message["clients"][0]
                client["name"] = self.name
                client["alsa"] = self.alsa
                receiver = Receiver(**client)
                receiver()
            else:
                logging.debug("Receiver for server already started")

        #if "message" in message:
        #    logging.debug(message["message"])
        #else:
        #    logging.debug(message)

    def on_error(self, ws, error):
        logging.info("ON_ERROR %s" % error)

    def on_close(self, ws):
        logging.info("### closed ###")

    def on_open(self, ws):
        first_message = json.dumps({
            "register": "",
            "name": self.name,
            "key": self.key,
            "port": self.port,
        })
        ws.send(first_message)


    def cleanup(self):
        logging.info("Performing cleanup.")
        for receiver in Receiver.receivers.copy():
            logging.debug("Shutting down receiver for {}.".format(receiver))
            Receiver.receivers[receiver].stop()
        if self.emitter is not None:
            logging.debug("Not shutting down emitter.")

    def get_port(self):
        logging.debug('Discovering... delay={}ums'.format(self.upnp_client.discoverdelay))
        ndevices = self.upnp_client.discover()
        logging.debug('{} device(s) detected'.format(ndevices))
        # select an igd
        logging.debug("Selecting IGD")
        self.upnp_client.selectigd()
        # display information about the IGD and the internet connection
        logging.debug('local ip address: {}'.format(self.upnp_client.lanaddr))
        externalipaddress = self.upnp_client.externalipaddress()
        logging.debug('external ip address: {}'.format(externalipaddress))
        logging.debug(self.upnp_client.statusinfo())
        logging.debug(self.upnp_client.connectiontype())

        while True and self.port < 65536:
            r = self.upnp.getgenericportmapping(self.port)
            if r is None:
                break
            logging.debug("port {} is occupied. Trying port {}".format(self.port, self.port + 2))
            self.port += 2
        self.upnp_client.addportmapping(self.port,
                                        'TCP',
                                        self.upnp_client.lanaddr,
                                        self.port,
                                        '{} - Matriz emitter'.format(self.name),
                                        '')

    def start_loop(self):
        self.loop = threading.Thread(target=GObject.MainLoop().run)
        self.loop.daemon = True
        self.loop.start()

    def __call__(self):
        self.start_loop()
        # self.get_port()
        self.emitter = Emitter(port=self.port, record=self.record, name=self.name, local=self.local, alsa=self.alsa)
        self.emitter()
        while not check_rtsp_port(port=self.port)[0]:
            time.sleep(0.1)
        # self.jack_client = JackClient()
        # self.jack_client()
        logging.debug("ip: {}; port:{}".format(self.receive_from_ip, self.receive_from_port))
        if self.local:
            if self.receive_from_ip is not None and self.receive_from_port is not None:
                counter = 0
                while not check_rtsp_port(
                        address=self.receive_from_ip,
                        port=self.receive_from_port
                        )[0]:
                    time.sleep(1)
                    counter += 1
                    if counter >= 5:
                        logging.error("Cannot connect to rtsp://{}:{}".format(
                            self.receive_from_ip,
                            self.receive_from_port))
                        exit(1)
                logging.debug("Starting receiver from config file: {}:{}".format(self.receive_from_ip, self.receive_from_port))
                receiver = Receiver(**{"ip": self.receive_from_ip, "port": self.receive_from_port, "name": self.name, "local": self.local, "alsa": self.alsa})
                receiver()
                while True:
                    time.sleep(.1)
        else:
            self.connect()

    def connect(self):
        time.sleep(random.randrange(0, 2**self.connection_attempts))
        self.connection_attempts += 1
        # websocket.enableTrace(True)
        ws = websocket.WebSocketApp(self.config_server_url,
                                    on_message=self.on_message,
                                    on_error=self.on_error,
                                    on_close=self.on_close)
        ws.on_open = self.on_open
        if self.config_server_url.startswith("wss://"):
            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_REQUIRED,
                                   "ca_certs": ca_cert,
                                   "ssl_version": ssl.PROTOCOL_TLSv1_2,
                                   "keyfile": client_pem,
                                   "certfile": client_crt})
        else:
            ws.run_forever()

    def debug(self):
        import code
        code.interact(local=locals())


if __name__ == "__main__":
    main()
