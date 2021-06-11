#!/usr/bin/env python3

import os
import time
import sys
import numpy as np
from pathlib import Path

from wib_cryo import get_addr_port
from wib import WIB

import argparse
parser = argparse.ArgumentParser(description='WIB Cryo DAQ')
parser.add_argument('-w', dest='wib', metavar='ip', help='wib ip address')
parser.add_argument('-o', '--outdir', metavar='output_directory', help='store data')
parser.add_argument('-n', '--nevents', metavar='num_of_events', 
                    type=int, default=10,
                    help='(optinal) default=10')
parser.add_argument('--buf', metavar='BUFFER',
                    type=int, choices=[0,1],
                    help='(optional) read only 1 buffer. default=0,1')

if __name__ == '__main__':
    args = parser.parse_args()
    addr, __ = get_addr_port(args.wib)
    
    if args.outdir is None:
        now = int(time.time())
        args.outdir = f'wib_spy_buffer-{now}'
    
    outpath = Path(args.outdir).expanduser()
    if os.path.isdir(outpath):
        print(f'ERROR: {outpath} already exsist')
        sys.exit(1)

    os.makedirs(outpath)
    print(f'acquring {args.nevents} events from {addr}')
    print(f'saving output to {outpath}')

    wib = WIB(addr)

    daq_kwargs = {}
    if args.buf == 0:
        daq_kwargs['buf1'] = False
    elif args.buf == 1:
        daq_kwargs['buf0'] = False

    for i in range(args.nevents):
        outfile = os.path.join(outpath, f'event_{i:05}')
        try:
            ts, data = wib.acquire_data(**daq_kwargs)
        except:
            print('Fail to get data from spy buffer')
            sys.exit(1)

        np.savez_compressed(outfile,
                            timestamps=ts,
                            data=data)

    print(f'DONE')
    sys.exit(0)
