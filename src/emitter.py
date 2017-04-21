#!/usr/bin/env python
import threading
import sys
import gi
import time
import logging
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GObject, GstRtspServer

import socket


TEST_PIPELINE = (
    'jackaudiosrc client-name={name} '
    '! audioconvert '
    '! audioresample '
    '! opusenc {encoding_options} '
    '! rtpopuspay name=pay0 ')


DEFAULT_PIPELINE = (
    'jackaudiosrc client-name={name} '
    '! audioconvert '
    '! audioresample '
    '! tee name="splitter" '
    '! queue '
    '! opusenc {encoding_options} '
    '! rtpopuspay name=pay0 splitter. '
    '! queue '
    '! wavenc '
    '! filesink location="{filename}.wav"')

ALSA_PIPELINE = (
    'alsasrc '
    '! audioconvert '
    '! audioresample '
    '! opusenc {encoding_options} '
    '! rtpopuspay name=pay0 ')


class Emitter():
    """ Audio emitter. """
    emitters = {}

    def __init__(self, *args, **kwargs):
        """
        gst-launch-example:
            GST_DEBUG="level:8" gst-launch-1.0 -m alsasrc device="hw:0" \
                    ! level ! audioconvert ! audioresample !  opusenc \
                    ! rtpopuspay ! udpsink host=127.0.0.1 port=9999 \
                    2>&1 | grep "message:" | sed "s/.*\(message: .*\)/\1/"
        TODO:
            Add encoding options
            Test src
        """
        self.ip = kwargs.get("ip", '127.0.0.1')
        self.port = kwargs.get("port", 8554)
        self.local = kwargs.get("local", False)
        self.name = kwargs.get("name", "client")
        self.encoding_options = kwargs.get("encoding_options", "")
        self.record = kwargs.get("record", False)
        self.alsa = kwargs.get("alsa", False)
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
            jack_name = "{}-mic".format(self.name)
        else:
            jack_name = self.name

        self.pipeline = Gst.Pipeline.new("my-mic")

        if self.alsa:
            logging.debug("ALSA ON")
            src = Gst.ElementFactory.make('alsasrc')
            #src.set_property('device', "hw:0")
        else:
            logging.debug("JACK ON")
            src = Gst.ElementFactory.make('jackaudiosrc')
            src.set_property('client-name', jack_name)

        if self.record:
            logging.debug("RECORDING ON - fake!")
            queue = Gst.ElementFactory.make('queue')
            tee = Gst.ElementFactory.make('tee')
            tee.set_property('name', 'splitter')
            wavenc = Gst.ElementFactory.make('wavenc')
            filesink = Gst.ElementFactory.make('filesink')
            filesink.set_property('location', "-".join(time.asctime().split()))


        level = Gst.ElementFactory.make('level')
        aconvert = Gst.ElementFactory.make('audioconvert')
        aresample = Gst.ElementFactory.make('audioresample')
        enc = Gst.ElementFactory.make('opusenc')
        rtppay = Gst.ElementFactory.make('rtpopuspay')
        sink = Gst.ElementFactory.make('udpsink')

        sink.set_property('host', self.ip)
        sink.set_property('port', self.port)
        logging.info("-EMITTER- init emitter with ip: {} and port: {}".format(self.ip, self.port))


        self.pipeline.add(src)
        self.pipeline.add(level)
        self.pipeline.add(aconvert)
        self.pipeline.add(aresample)

        #if self.record:
        #    add queues tees filesink....

        self.pipeline.add(enc)
        self.pipeline.add(rtppay)
        self.pipeline.add(sink)

        src.link(level)
        level.link(aconvert)
        aconvert.link(aresample)
        aresample.link(enc)
        enc.link(rtppay)
        rtppay.link(sink)

        #if self.record:
        #    link queues tees filesink....

        if self.local == False and self.pd_socket != None:
            self.bus = self.pipeline.get_bus()
            self.bus.add_signal_watch()
            self.bus.connect('message', self.on_message)

    def __call__(self):
        logging.info("-EMITTER- Sending to {} at port {}".format(self.ip, self.port))
        self.pipeline.set_state(Gst.State.PLAYING)

    def stop(self):
        self.pipeline.set_state(Gst.State.NULL)
        logging.info("Emitter for {} STOPPED".format(self.name))
        if self.pd_socket:
            self.pd_socket.close()
        # self.loop.quit()


    def on_message(self, bus, message):
        s = Gst.Message.get_structure(message)

        if message.type == Gst.MessageType.ELEMENT:
            """
            TODO:
            Save to file or send to pd or send over websockets
            """
            if str(Gst.Structure.get_name(s)) == 'level':
                rms = s.get_value('rms')
                peak = s.get_value('peak')
                decay = s.get_value('decay')
                #logging.info("-EMITTER- RMS: {}; PEAK: {}; DECAY: {}".format(rms, peak, decay))
                self.pd_socket.sendall("{}{}".format(rms, ";\n"))



if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    GObject.threads_init()
    Gst.init(None)
    loop = GObject.MainLoop()
    emitter = Emitter(record=True, alsa=True)
    emitter()
    try:
        logging.debug("Started main loop")
        loop.run()
    except KeyboardInterrupt:
        logging.debug("Caught keyboard interrupt")
        emitter.pipeline.set_state(Gst.State.NULL)
        loop.quit()
        logging.debug("Mainloop Stopped")

