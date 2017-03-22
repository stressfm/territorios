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

LOGGER_FORMAT_DEBUG = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOGGER_FORMAT_INFO = '%(message)s'
logger = logging.getLogger(__name__)

def _create_parser():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-d', '--debug', action="store_true", default=False)
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
    make_test(args.filename)

def make_test(name):
    """
    supervisorctl stop matriz-client
    jack_connect system:capture_1 system:playback_1
    jack_connect system:capture_2 system:playback_2
    jack_rec -f nuno2.wav -d 20 system:capture_1 system:capture_2

    """
    ssh = ["ssh", "pi@10.10.0.5"]
    off_matriz = ["supervisorctl", "stop", "matriz-client"]
    jack_conn1 = ["jack_connect", "system:capture_1", "system:playback_1"]
    jack_conn2 = ["jack_connect", "system:capture_2", "system:playback_2"]
    prepare = Popen(ssh + off_matriz + [";"] + jack_conn1 + [";"] + jack_conn2, stdout=PIPE, stderr=PIPE)
    prepare.wait()

    audio_tests = ["meio", "3_4"]
    audio_tests = ["3_4"]

    osci = "oscil_440_L_R_C.wav"
    for mtest in audio_tests:
        input("Start....")
        jack_rec = ["jack_rec", "-f", name + '_' + mtest + '.wav', "-d", "15", "system:capture_1", "system:capture_2"]
        aplay = ["aplay", osci]
        j = Popen(ssh + jack_rec, stdout=PIPE, stderr=PIPE)
        a = Popen(aplay, stdout=PIPE, stderr=PIPE)
        a.wait()
    Popen(['scp', "pi@10.10.0.5:" + name + '_*.wav', '.']).wait()
    Popen(['scp', name + '_meio.wav', name + '_3_4.wav', 'lulu@192.168.1.13:Music']).wait()


if __name__ == "__main__":
    main()
