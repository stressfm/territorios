#!/usr/bin/env python3
"""
#tags:
#sys_deps:
#py_deps:
"""
import argparse
import sys
import logging
from subprocess import Popen, PIPE

FINAL_DEST=""

LOGGER_FORMAT_DEBUG = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOGGER_FORMAT_INFO = '%(message)s'
logger = logging.getLogger(__name__)

def _create_parser():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-d', '--debug', action="store_true", default=False)
    parser.add_argument('-I', '--pi-address', type=str, nargs="?")
    parser.add_argument('-D', '--destination', type=str, nargs="?")
    parser.add_argument('filename', type=str, nargs="?")

    return parser

def main(arguments=sys.argv[1:]):
    parser = _create_parser()
    args = parser.parse_args(arguments)
    if args.debug:
        logging.basicConfig(
            format=LOGGER_FORMAT_DEBUG,
            level=logging.DEBUG
        )
    else:
        logging.basicConfig(
            format=LOGGER_FORMAT_INFO,
            level=logging.INFO
        )

    logging.debug("Starting program")
    logging.info("Starting program")
    print("{}".format(args))
    #play_test_audio()
    #exit(0)
    make_test(args.filename, args.pi_address)
    # Copy file if destination is not empty
    if args.destination:
        #Popen(['scp', args.filename + '_meio.wav', args.filename + '_3_4.wav', args.destination]).wait()
        Popen(['scp', args.filename + '_meio.wav', args.destination]).wait()

def play_test_audio():
    """
    gst-launch-1.0 filesrc location=/home/pi/oscil_440_L_R_C.wav ! wavparse ! audioconvert ! audioresample ! jackaudiosink
    """
    cmd = ["gst-launch-1.0 filesrc location=/home/pi/oscil_440_L_R_C.wav ! wavparse ! audioconvert ! audioresample ! jackaudiosink"]
    Popen(cmd, shell=True, stdout=PIPE, stdin=PIPE).wait()

def make_test(name, ip):
    """
    supervisorctl stop matriz-client
    jack_connect system:capture_1 system:playback_1
    jack_connect system:capture_2 system:playback_2
    jack_rec -f nuno2.wav -d 20 system:capture_1 system:capture_2

    """
    #ssh = ["ssh", "pi@" + ip]
    #off_matriz = ["supervisorctl", "stop", "matriz-client"]
    #jack_conn1 = ["jack_connect", "system:capture_1", "system:playback_1"]
    #jack_conn2 = ["jack_connect", "system:capture_2", "system:playback_2"]
    #prepare = Popen(ssh + off_matriz + [";"] + jack_conn1 + [";"] + jack_conn2, stdout=PIPE, stderr=PIPE)
    #prepare.wait()

    audio_tests = ["meio", "3_4"]
    audio_tests = ["meio"]

    osci = "oscil_440_L_R_C.wav"
    for mtest in audio_tests:
        #input("Start...{}".format(mtest))
        print("Start...{}".format(mtest))
        jack_rec = ["jack_rec", "-f", name + '_' + mtest + '.wav', "-d", "15", "system:capture_1", "system:capture_2"]
        #aplay = ["aplay", osci]
        #j = Popen(ssh + jack_rec, stdout=PIPE, stderr=PIPE)
        j = Popen(jack_rec, stdout=PIPE, stderr=PIPE)
        #a = Popen(aplay, stdout=PIPE, stderr=PIPE)
        #a.wait()
        play_test_audio()
        j.wait()
    #Popen(['scp', "pi@" + ip + ":" + name + '_*.wav', '.']).wait()


if __name__ == "__main__":
    main()
