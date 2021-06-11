#!/usr/bin/env python3

from wib_cryo import get_addr_port
from wib import WIB
import wib_pb2 as wibpb

import argparse
parser = argparse.ArgumentParser(description='Python version of the wib_client utility')
parser.add_argument('-w', dest='wib', metavar='ip', help='wib ip address')
parser.add_argument('--femb', type=int, choices=range(4), nargs='+', required=True,
        help='FEMB number(s)')

if __name__ == "__main__":
    args = parser.parse_args()
    addr, __ = get_addr_port(args.wib)

    wib = WIB(addr)
    req = wib.defaults()

    for i in args.femb:
        req.fembs[i].enabled = True

    rep = wibpb.Status()
    wib.send_command(req, rep)
    print(rep.extra.decode('ascii'))
    print('Successful: ',rep.success)
