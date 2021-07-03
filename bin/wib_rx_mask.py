#!/usr/bin/env python3

from wib_cryo import get_addr_port
from wib import WIB
import wib_pb2 as wibpb

import argparse
parser = argparse.ArgumentParser(
    description='Python version of the wib_client utility'
)
parser.add_argument('-w', dest='wib', metavar='ip', help='wib ip address')
parser.add_argument(
    '--femb', type=int, choices=range(4),
    default=[], nargs='+', help='FEMB number(s)'
)
parser.add_argument(
    'rx_mask', 
    type=lambda x: int(x, 0),
    default=0, nargs='?',
)

if __name__ == "__main__":
    args = parser.parse_args()
    addr, __ = get_addr_port(args.wib)

    if len(args.femb) > 0:
        for i in range(4):
            if i in args.femb: continue
            args.rx_mask |= (0xf << (i*4))

    cmd = f'mem 0xa00c0008 {hex(args.rx_mask)}'
    print(f'[{addr}] {cmd}')


    wib = WIB(addr)
    req = wibpb.Script()
    rep = wibpb.Status()

    req.script = cmd.encode()
    req.file = False
    wib.send_command(req, rep)
    print(f'Successful: {rep.success}')
