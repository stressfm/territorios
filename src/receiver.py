#!/usr/bin/python
import threading
import logging
import gi
import time
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject

#from utils import check_rtsp_port


DEFAULT_PIPELINE = (
    'rtspsrc location="rtsp://{ip}:{port}/{mount}" latency={latency} port-range="8556-8600" '
    '! rtpopusdepay '
    '! opusdec'
    '! audioconvert'
    '! audioresample'
    '! jackaudiosink client-name={name}')

ALSA_PIPELINE = (
    'rtspsrc location="rtsp://{ip}:{port}/{mount}" latency={latency} port-range="8556-8600" '
    '! rtpopusdepay '
    '! opusdec'
    '! audioconvert'
    '! audioresample'
    '! alsasink')

logger = logging.getLogger(__name__)


class Receiver():
    """ Audio Receiver. """

    receivers = {}

    def __init__(self, *args, **kwargs):
        """
        gst-launch-example:
            GST_DEBUG="level:8" gst-launch-1.0 -m udpsrc port=9999 caps="application/x-rtp" \
                ! rtpopusdepay ! opusdec ! audioconvert ! audioresample ! level \
                ! alsasink device="hw:0" \
                2>&1 | grep "message:" | sed "s/.*\(message: .*\)/\1/"
        TODO:
            Add encoding options
            Test src
        """
        self.name = kwargs.get("name", "pa")
        self.alsa = kwargs.get("alsa", False)
        self.ip = kwargs.get("ip", "127.0.0.1")
        self.port = kwargs.get("port", 8554)
        self.local = kwargs.get("local", False)
        self.latency = kwargs.get("latency", 0)
        self.pd_socket = None
        if kwargs.get('pd', False):
            # pd = "ip:port"
            try:
                pd_host, pd_port = kwargs.get('pd').split(':')
                self.pd_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.pd_socket.settimeout(5.0)
                self.pd_socket.connect((pd_host, pd_port))
            except:
                pass


        if self.local:
            jack_name = "{}-pa".format(self.name)
        else:
            jack_name = self.name

        self.pipeline = Gst.Pipeline.new("my-pa")

        src = Gst.ElementFactory.make('udpsrc')
        src.set_property("port", self.port)
        src.set_property("caps", Gst.Caps.from_string("application/x-rtp"))
        rtpdepay = Gst.ElementFactory.make('rtpopusdepay')
        dec = Gst.ElementFactory.make('opusdec')
        aconvert = Gst.ElementFactory.make('audioconvert')
        aresample = Gst.ElementFactory.make('audioresample')
        level = Gst.ElementFactory.make('level')

        if self.alsa:
            logging.debug("ALSA ON")
            sink = Gst.ElementFactory.make('alsasink')
            sink.set_property('device', "hw:0")
        else:
            logging.debug("JACK ON")
            sink = Gst.ElementFactory.make('jackaudiosink')
            sink.set_property('client-name', jack_name)

        self.pipeline.add(src)
        self.pipeline.add(rtpdepay)
        self.pipeline.add(dec)
        self.pipeline.add(aconvert)
        self.pipeline.add(aresample)
        self.pipeline.add(level)
        self.pipeline.add(sink)

        #if self.record:
        #    add queues tees filesink....

        src.link(rtpdepay)
        rtpdepay.link(dec)
        dec.link(aconvert)
        aconvert.link(aresample)
        aresample.link(level)
        level.link(sink)

        #counter = 0
        #while not check_rtsp_port(address=self.ip, port=self.port)[0]:
        #    counter += 1
        #    time.sleep(.5)
        #    if counter > 5:
        #        logging.debug("Could not connect to {} at port {}".format(self.ip, self.port))
        #        exit(1)


        if self.local == False and self.pd_socket != None:
            self.bus = self.pipeline.get_bus()
            self.bus.add_signal_watch()
            self.bus.connect("message", self.on_message)

    def __call__(self):
        self.receivers[self.name] = self
        self.pipeline.set_state(Gst.State.PLAYING)
        logging.info("-RECEIVER-Receiving at port {}".format(self.port))


    def punch_udp_hole(self):
        # Must establish connection to remote emitter first so to
        # open port for receiving in the local router
        # Emitter doesn't have to listen to connection but must set the source port
        # port to the same of this connection
        # https://tools.ietf.org/html/rfc5128#section-3.3

        # TODO:
        # It is possible that ports are not available
        # We must check that receiver is getting data, and if not try another port
        # Right now were using same dest and src ports (which cannot work if we use emitter
        # and receiver)
        # Maybe we need a negotiation logic:
        # Open a udp socket at port, send connection information to config server
        # wait for packet, retry until packet receive. close connection.
        # Start receiver once we have connection

        # Open hole
        s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        # Set (bind) port to the one that will be used emitter (dest port)
        s.bind(('', self.port))
        # Use port that will be the source port (bind-port) of emitter
        s.connect((self.ip, self.port))
        # The string here is irrelevant, remote emitter will not get it
        # It is just meant for router to establish the ip/port pair to forward
        # connections to us
        s.sendall(b'some random string')
        s.close()

        # Wait for helo to confirm hole opened
        # bind to same port used to open the hole
        s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.bind(('', self.port))
        s.settimeout(5.0)
        data, addr = s.recvfrom(1024)
        s.close()
        if not data:
            self.port += 1
            return None
        if data == r'some random string':
            return addr


    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self.pipeline.set_state(Gst.State.NULL)
        elif t == Gst.MessageType.ERROR:
            self.pipeline.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print("Error: {} {}".format(err, debug))
        elif t == Gst.MessageType.ELEMENT:
            s = Gst.Message.get_structure(message)
            if str(Gst.Structure.get_name(s)) == 'level':
                rms = s.get_value('rms')
                peak = s.get_value('peak')
                decay = s.get_value('decay')
                #logging.info("-RECEIVER- RMS: {}; PEAK: {}; DECAY: {}".format(rms, peak, decay))
                self.pd_socket.sendall("{}{}".format(rms, ";\n"))


    def stop(self):
        self.pipeline.set_state(Gst.State.NULL)
        logging.info("Receiver for {} STOPPED".format(self.name))
        logging.debug("receivers: {}".format(Receiver.receivers))
        del Receiver.receivers[self.name]
        logging.debug("receivers: {}".format(Receiver.receivers))
        # self.loop.quit()


if __name__ == '__main__':
    #import sys
    #if len(sys.argv) > 1:
    #    ip = sys.argv[1]
    #else:
    #    ip = "192.168.1.92"
    logging.basicConfig(level=logging.DEBUG)
    GObject.threads_init()
    Gst.init(None)
    receiver = Receiver(alsa=True)
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
