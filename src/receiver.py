#!/usr/bin/python
import threading
import logging
import gi
import time
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject

from utils import check_rtsp_port


DEFAULT_PIPELINE = (
    'rtspsrc location="rtsp://{ip}:{port}/{mount}" latency={latency} port-range="8556-8600" '
    '! rtpopusdepay '
    '! opusdec'
    '! audioconvert'
    '! audioresample'
    '! jackaudiosink client-name={name}')


logger = logging.getLogger(__name__)


class Receiver():
    """ Audio Receiver. """

    receivers = {}

    def __init__(self, *args, **kwargs):
        self.name = kwargs.get("name", "receiver")
        self.ip = kwargs.get("ip", "127.0.0.1")
        self.port = kwargs.get("port", 8554)
        self.local = kwargs.get("local", False)
        self.mount = kwargs.get("mount", "stream")
        self.latency = kwargs.get("latency", 0)
        if self.local:
            jack_name = "{}-receiver".format(self.name)
        else:
            jack_name = self.name
        self.pipeline = kwargs.get("pipeline", DEFAULT_PIPELINE).format(
            ip=self.ip,
            port=str(self.port),
            mount=self.mount,
            latency=str(self.latency),
            name=jack_name)
        logging.info("Running receiver for rtsp://{ip}:{port}/{mount}".format(
            ip=self.ip,
            port=self.port,
            mount=self.mount))
        counter = 0
        while not check_rtsp_port(address=self.ip, port=self.port)[0]:
            counter += 1
            time.sleep(.5)
            if counter > 5:
                logging.debug("Could not connect to {} at port {}".format(self.ip, self.port))
                exit(1)

        self.pipeline = Gst.parse_launch(self.pipeline)
        self.bus = self.pipeline.get_bus()
        self.bus.connect("message", self.on_message)
        """
        try:
            self.loop.run()
        except KeyboardInterrupt:
            self.loop.quit()
            self.pipeline.set_state(Gst.State.NULL)
        """
    def __call__(self):
        self.receivers[self.name] = self
        self.pipeline.set_state(Gst.State.PLAYING)


    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self.player.set_state(Gst.State.NULL)
        elif t == Gst.MessageType.ERROR:
            self.player.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print("Error: {} {}".format(err, debug))

    def stop(self):
        self.pipeline.set_state(Gst.State.NULL)
        logging.info("Receiver for {} STOPPED".format(self.name))
        logging.debug("receivers: {}".format(Receiver.receivers))
        del Receiver.receivers[self.name]
        logging.debug("receivers: {}".format(Receiver.receivers))
        # self.loop.quit()


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        ip = sys.argv[1]
    else:
        ip = "192.168.1.92"
    logging.basicConfig(level=logging.DEBUG)
    GObject.threads_init()
    Gst.init(None)
    receiver = Receiver(ip=ip)
    receiver()
    loop = GObject.MainLoop()
    try:
        loop.run()
        logging.debug("Started main loop")
    except KeyboardInterrupt:
        logging.debug("Caught keyboard interrupt")
        receiver.stop()
        loop.quit()
        logging.debug("Mainloop Stopped")
        receiver.pipeline.set_state(Gst.State.NULL)
        logging.debug("Set pipeline state to NULL")
