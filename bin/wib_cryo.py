#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import argparse
import inspect
import itertools
import numpy as np
from multiprocessing import Process

from pyrogue.interfaces import SimpleClient as pr_SimpleClient

# TODO(2021-06-17 kvtsang) Remove after upgrading to rogue-v5.7.0
class _SimpleClient(pr_SimpleClient):
  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self._stop()

  def exec(self, path, arg=None):
    return self._remoteAttr(path, '__call__', arg)

if hasattr(pr_SimpleClient, '__enter__'):
  SimpleClient = pr_SimpleClient
else:
  SimpleClient = _SimpleClient

def version(**kwargs):
    print( '''
=================================
= wib_cryo.py: WIB-CRYO scripts =
=                               =
=           v0.0.1              =
=        Patrick Tsang          =
=   kvtsang@slac.stanford.edu   =
=                               =
=================================
    ''')

def usage(**kwargs):
    PROG='wib_cryo.py'

    version()
    print(f'''
Usage:
    {PROG} init --femb FEMBS [--cold]
        Initialize cryo for given FEMBS, optionally use cold setting.
        Use room temperature setting by default.
        Example: {PROG} init --femb 0 1 2 3 --cold

    {PROG} reset_asic --femb FEMBS 
        Reset asic by toggling GlblRstPolarity
        Disable SampClkEn and SR0Polarity after reset
        Example: {PROG} reset_asic --femb 0 1 2 3

    {PROG} config_asic --asic ASICS --val VALUE
        WriteColData for all channels in the given ASICS
        Example: {PROG} config_asic --asic 2 3 --val 0x390

    {PROG} config_asic_ch --asic ASICS --ch CHANNELS --val VALUE
        WritePixelData for the given ASICS and CHANNELS
        Example: {PROG} config_asic_ch --asic 0 1 --ch 32 50 101 --val 0x390

    {PROG} enable_ramp --femb FEMBS
        Set internal ramp mode for FEMBS.
        Also change LaneBitOrder and toggle SR0Polarity to take effect.
        Use "{PROG} disable_ramp" to switch back to data mode.

    {PROG} disable_ramp --femb FEMBS
        Disable ramp mode. Use in conjuction with "enable_ramp" command.

    {PROG} help
        Show help (this text).

    {PROG} version
        Show version.
    ''')

def get_addr_port(wib_addr=None):
    """
    Get wib addrees and port (for rogue access).
    If `addr` is `None`, get from shell env $WIB_ADDR and $WIB_ROGUE_PORT

    Parameters
    ----------
    wib_addr: str 
        WIB address, e.g. '192.168.121.1:9099'
        port number is optional

    Returns
    -------
    wib_addr: str
        WIB IP address 
    wib_port: int
        WIB port number for rogue
    """

    # get rogue port from $WIB_ROGUE_PORT (default 9099)
    # overrided by addr input
    wib_port = os.getenv('WIB_ROGUE_PORT', '9099')

    # get wib ip address from $WIB_ADDR if not specify
    if wib_addr is None:
        wib_addr = os.getenv('WIB_ADDR')

        if wib_addr  is None:
            print('WIB address not set', file=sys.stderr)
            sys.exit(1)
    elif ':' in wib_addr:
        wib_addr, wib_port = wib_addr.split(':')
        wib_port = int(wib_port)

    wib_port = int(wib_port)

    return wib_addr, wib_port

def rogue_getDisp(addr, port, var_list):
    """
    Read list of rogue variables

    Parameters
    ----------
    addr: str
        WIB IP address
    port: int
        rogue port
    var_list: list
        a list of variables to be read
    """

    with SimpleClient(addr, port) as client:
        for var in var_list:
            ret = client.getDisp(var)
            print(f'[{addr}:{port}] get {var} -> {ret}')

def rogue_set(addr, port, pars, pause=0):
    """
    Set values to a list of rogue variables

    Parameters
    ----------
    addr: str
        WIB IP address
    port: int
        rogue port
    pars: list of tuple 
        list of (path, value) pairs
    """

    with SimpleClient(addr, port) as client:
        for path, val in pars:
            disp_val = hex(val) if isinstance(val, int) else val
            print(f'[{addr}:{port}] set {path} <- {disp_val}')
            client.set(path, val)
            if pause > 0: time.sleep(pause)

def rogue_exec(addr, port, cmds, pause=0):
    """
    Set values to a list of rogue variables

    Parameters
    ----------
    addr: str
        WIB IP address
    port: int
        rogue port
    cmds: list of tuple 
        list for (cmd, args)
    """

    with SimpleClient(addr, port) as client:
        for cmd, val in cmds:
            disp_val = hex(val) if isinstance(val, int) else val
            print(f'[{addr}:{port}] exe {cmd} {disp_val}')
            client.exec(cmd, val)
            if pause > 0: time.sleep(pause)

def ssh_cmd(addr, cmd):
    os.system(f'ssh root@{addr} \'{cmd}\'')

def config_pll(addr, port):
    print(f'[{addr}:{port}] Configuring PLL')

    prefix = 'cryoAsicGen1.WibFembCryo.MMCM7Registers'
    with SimpleClient(addr, port) as client:
        client.set(f'{prefix}.enable', True)
        client.exec('root.ReadAll')
        client.set(f'{prefix}.CLKOUT3HighTime', 1)
        client.set(f'{prefix}.CLKOUT3LowTime', 1)
        client.exec('root.ReadAll')

def get_mmcm7_status(addr, port):
    prefix = 'cryoAsicGen1.WibFembCryo.MMCM7Registers'
    variables = [f'{prefix}.{x}' 
            for x in ['enable', 'CLKOUT3HighTime', 'CLKOUT3LowTime']]
    rogue_getDisp(addr, port, variables)

def load_fw(addr):
    print(f'Loading remote wib_top.bit at {addr}'
           ' && echo "wib_top.bit" > /sys/class/fpga_manager/fpga0/firmware')
    _ssh_cmd(addr, cmd)

def start_server(addr):
    print(f'starting rogue server at {addr}')
    ssh_cmd(addr, './start_cryo_server')

def load_yml(addr, port, yml_file):
    """
    Load yml files.

    Parameters
    ----------
    addr: str
        WIB IP address
    port: int
        rogue port
    yml_file: str or list(str)
        file path relative to /etc/cryo/yml on the WIB (not host)
        For loading multiple files, set `yml_file` as a list of paths
    """

    files = [yml_file] if isinstance(yml_file, str) else yml_file
    cmds = [('root.LoadConfig', os.path.join('/etc/cryo/yml', f))
            for f in files]
    rogue_exec(addr, port, cmds)

def load_default_yml(addr, port, femb, cold):
    """
    Load default yml config for FEMB{0,1,2,3}

    Parameters
    ----------
    addr: str
        WIB IP address
    port: int
        rogue port
    femb: int or list(int)
        FMEB number(s)
    cold: bool
        Use cold settings if True. Otherwise use room settings
    """

    fembs = [femb] if isinstance(femb, int) else femb

    cond = 'ColdTemp' if cold else 'RoomTemp' 
    files = []
    for i in fembs:
        files.append(f'wib_cryo_config_ASIC_ExtClk_{cond}_asic{2*i}.yml')
        files.append(f'wib_cryo_config_ASIC_ExtClk_{cond}_asic{2*i+1}.yml')
    load_yml(addr, port, files)

def is_rx_locked(addr, port, femb, timeout, min_locked_cnt=10):
    """
    Check whether all lanes are locked. Get status every second.
    Required stable locked for multiple consecutive check.

    Parameters
    ----------
    addr: str
        WIB IP address
    port: int
        rogue port
    femb: int of list(int)
        list of active FEMB(s)
    timeout: int
        timeout in seconds
    min_locked_cnt: int
        min good locked in a row
    """

    fembs = [femb] if isinstance(femb, int) else femb

    def _check(addr, port):
        cnts = np.array([0, 0, 0, 0]) # counters for consecutive locked state in a row
        with SimpleClient(addr, port) as client:
            for i in fembs:
                client.set(f'cryoAsicGen1.WibFembCryo.SspGtDecoderReg{i}.enable', True)

            while cnts[fembs].min() < min_locked_cnt:
                for i in fembs:
                    ret = client.get(f'cryoAsicGen1.WibFembCryo.SspGtDecoderReg{i}.Locked')

                    if ret == 0xf: 
                        cnts[i] += 1
                    else:
                        cnts[i] = 0
                time.sleep(1)

    p = Process(target=_check, args=(addr, port))
    p.start()
    p.join(timeout=timeout)
    p.terminate()
    return p.exitcode == 0

def reset_asic(addr, port, femb):
    fembs = [femb] if isinstance(femb, int) else femb

    pars = []
    for i in fembs:
        var = f'cryoAsicGen1.WibFembCryo.AppFpgaRegisters.GlblRstPolarity{i}'
        pars.append((var, False))
        pars.append((var, True))

    rogue_set(addr, port, pars, pause=1)

    clk(addr, port, 0)
    sr0(addr, port, 0)

def clk(addr, port, flag):
    rogue_set(addr, port, [('cryoAsicGen1.WibFembCryo.AppFpgaRegisters.SampClkEn', flag)])

def toggle_clk(addr, port):
    path = 'cryoAsicGen1.WibFembCryo.AppFpgaRegisters.SampClkEn'
    pars = [(path, False), (path, True)]
    rogue_set(addr, port, pars)

def sr0(addr, port, flag):
    rogue_set(addr, port, [('cryoAsicGen1.WibFembCryo.AppFpgaRegisters.SR0Polarity', flag)])

def toggle_sr0(addr, port):
    path = 'cryoAsicGen1.WibFembCryo.AppFpgaRegisters.SR0Polarity'
    pars = []
    for i in range(3):
        pars.append((path, False))
        pars.append((path, True))

    rogue_set(addr, port, pars[:2])
    time.sleep(10)
    rogue_set(addr, port, pars)

def enable_clk(addr, port, femb):
    RETRIES = 2
    TIMEOUT = 30
    fembs = [femb] if isinstance(femb, int) else femb

    print(f'[{addr}:{port}] Enabling clock')
    i = 0
    success = False
    while i <= RETRIES and not success:
        if i > 0:
            print(f'[{addr}] Enabling clock, retry #{i}')
            clk(addr, port, False)

        clk(addr, port, True)
        sr0(addr, port, True)
        time.sleep(5)
        sr0(addr, port, False)

        success = is_rx_locked(addr, port, fembs, timeout=TIMEOUT)
        i += 1

    if not success:
        print(f'[{addr}:{port}] Failed to lock rxLink', file=sys.stderr)
        sys.exit(1)

def config_asic(addr, port, asic, val):
    asics = [asic] if isinstance(asic, int) else asic
    cmd = [(f'cryoAsicGen1.WibFembCryo.CryoAsic{i}.WriteColData', val)
            for i in asics]
    rogue_exec(addr, port, cmd)
    
def config_asic_ch(addr, port, asic, ch, val):
    asics = [asic] if isinstance(asic, int) else asic
    chs = [ch] if isinstance(ch, int) else ch 

    cmds = []
    for a, c in itertools.product(asics, chs):
        cmds.append((f'cryoAsicGen1.WibFembCryo.CryoAsic{asic}.RowCounter', ch))
        cmds.append((f'cryoAsicGen1.WibFembCryo.CryoAsic{asic}.WritePixelData', val))
    rogue_exec(addr, port, cmds)

def set_ramp(addr, port, femb, flag):
    femb = [femb] if isinstance(femb, int) else femb

    if flag:
        action = 'Enabling'
        mode = 0x3
        bit_order = 0xf
    else:
        action = 'Disabling'
        mode = 0
        bit_order = 0

    print(f'[{addr}:{port}] {action} internal ramp for FEMB {femb}')

    pars = []
    for i in femb:
        pars.append((f'cryoAsicGen1.WibFembCryo.CryoAsic{2*i}.encoder_mode_dft', mode))
        pars.append((f'cryoAsicGen1.WibFembCryo.CryoAsic{2*i+1}.encoder_mode_dft', mode))
        pars.append((f'cryoAsicGen1.WibFembCryo.SspGtDecoderReg{i}.enable', True))
        pars.append((f'cryoAsicGen1.WibFembCryo.SspGtDecoderReg{i}.LaneBitOrder', bit_order))
    rogue_set(addr, port, pars)

    toggle_sr0(addr, port)

def enable_ramp(addr, port, femb):
    set_ramp(addr, port, femb, True)

def disable_ramp(addr, port, femb):
    set_ramp(addr, port, femb, False)

def init(addr, port, femb, cold):
    config_pll(addr, port)
    load_default_yml(addr, port, femb, cold)
    enable_clk(addr, port, femb)
    toggle_sr0(addr, port)
    print(f'[{addr}:{port}] WIB-CRYO initialzed, is_cold={cold}')

def _bind(parser, func, **kwargs):
    """
    Bind parser to a function.
    Auto generate known arguments.

    Parameters
    ----------
    parser: ArgumentParser
        parser to bind
    func: python function
        function binded to parser
    kwargs: dict
        additional keyword arguments for `add_parser`
    """

    p = parser.add_parser(func.__name__, **kwargs)
    
    for arg in inspect.getfullargspec(func).args:
        if arg == 'addr' or arg == 'port':
            continue
        elif arg == 'femb':
            p.add_argument('--femb',
                    choices=range(4), type=int, nargs='+',
                    required=True, help='FEMB number(s)')
        elif arg == 'cold':
            p.add_argument('--cold',
                    action='store_true',
                    help='Cold settings (optional), default: room temperature')
        elif arg == 'flag':
            p.add_argument('flag', type=int, choices=[0,1], help='0 or 1')
        elif arg == 'asic':
            p.add_argument('--asic', type=int, choices=range(8), 
                    nargs='+', required=True,
                    help='ASIC number(s)')
        elif arg == 'ch':
            p.add_argument('--ch', type=int, choices=range(128),
                    metavar='CH{0-127}', nargs='+', required=True,
                    help='Channel number(s)',
                    )
        elif arg == 'val':
            p.add_argument('--val', type=lambda x: int(x,0),
                    required=True, help='value to set')
        elif arg == 'yml_file':
            p.add_argument('-f', '--yml_file', nargs='+',
                    help='YML file path relative to /etc/wib/yml on the WIB')
        else:
            print(f'Bind: unkwonn argument {arg}')

    p.set_defaults(func=func)
            
def main():
    parser = argparse.ArgumentParser(description='WIB Cryo')
    parser.add_argument('-w', dest='wib', metavar='ip:<port>',
                        help='wib ip address')
    subparsers = parser.add_subparsers()

    _bind(subparsers, load_default_yml, aliases=['load'])
    _bind(subparsers, load_yml, aliases=['load'])
    _bind(subparsers, clk)
    _bind(subparsers, toggle_clk)
    _bind(subparsers, sr0)
    _bind(subparsers, toggle_sr0)
    _bind(subparsers, config_asic, aliases=['config'])
    _bind(subparsers, config_asic_ch, aliases=['config_ch'])
    _bind(subparsers, enable_clk)
    _bind(subparsers, enable_ramp)
    _bind(subparsers, reset_asic)
    _bind(subparsers, disable_ramp)
    _bind(subparsers, init)
    _bind(subparsers, version)
    _bind(subparsers, usage, aliases=['help'])

    args = parser.parse_args()
    addr, port = get_addr_port(args.wib)

    kwargs = vars(args).copy()
    kwargs.pop('wib')
    kwargs.pop('func')
    kwargs['addr'] = addr
    kwargs['port'] = port

    args.func(**kwargs)

if __name__ == '__main__':
    main()

