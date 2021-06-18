WIB Software at SLAC
====================
Setup Environment
-----------------
Do once for each session

```
source ~wib/setup.sh
```

WIB Monitoring
--------------
`wib_mon.py -w 192.168.121.1` for GUI

or 

`wib_mon.py -w 192.168.121.1 -c` for CLI output

Set DC2DC and LDO Voltages
--------------------------
```
wib_power_conf.py -w 192.168.121.1 --dc2dc <O1> <O2> <O3> <O4> --ldo <A0> <A1>
```

- voltage in units of V
- check `wib_power_confg.py -h` for default values
- all 4 FEMBs share the same set of DC2DC and LDO values (but ON/OFF individually)
- FEMBs are in OFF status after setting DC2DC and LDO values
- set 0V to disable any DC2DC or LDO

`wib_power_conf.py -w 192.168.121.1 --dc2dc 0 0 0 0 --ldo 2.5 0`
Only LDO_A0 is ON (and set to 2.5V), while all DC2DCs and LDO_A1 are not enable.

Power ON/OFF FEMB
-----------------
Turn ON all FEMBs
`wib_power.py -w 192.168.121.1 on on on on`

Turn OFF all FEMBs
`wib_power.py -w 192.168.121.1 off off off off`

Only turn on FEMB2 only
`wib_power.py -w 192.168.121.1 off off on off`

- if a FEMB is ON, no action will be taken

WIB Initialization
==================
**Notes(2021-06-11)**
- New script `wib_cryo.py` to replace `wib_init` and `reset_asic`.
- Check `wib_cryo.py help` for usage.
- No more json file. Use `wib_rx_mask.py` instead.

The following example show how to configure FEMB1 in room temperature.

After wib booted,
```
source ~wib/setup.sh

# Optinal for SLAC (since there is no timing module)
wib_client.py -w 192.168.121.1 timing_reset

# Power on FEMBs
power_cycle_fembs

# Init for room setting
wib_cryo.py init --femb 1

# Init for cold setting
wib_cryo.py init --femb 1 --cold
```

The `wib_cryo.py init` do the following in sequence:
1. config PLL: enable and set `MMCM7Registers`
2. load yaml config file to ASIC 
3. enable clock 'SampClkEn' and check for a stable `Locked`

To check timing status, do
```
wib_client.py -w 192.168.121.1 timing_status
```

If the pyrogue gui does not respond (especially after power cycle), 
try issue a reboot `wib_client.py -w 192.168.121.1 reboot`.

If it failed to get locked after a number of retries, 
try `power_cycle_fembs` (optional) and `wib_cryo.py reset_asic --femb 1`.
Then repeat `wib_cryo.py init --femb 1`.

Once the wib is initialized, configure ASICs for data mode
```
wib_cryo.py config_asic --asic 2 3 --val 0x390
```

Optionally, for internal ramping
```
wib_cryo.py enable_ramp --femb 1
```
To switch back to data mode,
```
wib_cryo.py disable_ramp --femb 1
```

Finally set the rx mask 
```
wib_rx_mask.py --femb 1
```

Spy Buffer Readout
==================
To check the wib spy buffer (FEMB1 in buffer 0):
```
wib_client.py -w 192.168.121.1 daqspy test.dat buf0
```

It should return `Successful: True`. Otherwise, spy buffer is not working.

To visualize the spy buffer, run `wib_dash.py`.
```
Dash is running on http://127.0.0.1:8050/
```
Open the url in a brower (on pc98921).

Record Data from Spy Buffer
===========================
```
wib_daq.py -w 192.168.121.1 -n 10 -o some_output_folder --buf 0
```

- this script take snapshots from spy buffer and save output as numpy (`npz`) files
- `-n` : number of events
- `-o` : set output folder
- `--buf`: read one buffer only (buf0 or buf1). If not set, read both.
- for help, `wib_daq.py -h`
- if there is any problem, test whether spy buffer works (see above)

Start rogue gui on host
=======================
python -m pyrogue --server=192.168.121.1:9099 gui &

How to update yml files
=======================

The yml files are tracked on github for bookkeeping:
[wib-cryo/yml](https://github.com/kvtsang/wib-cryo/tree/main/yml)

In case you want to change setting, you may do it either
1. edit directly on the  wib, or
2. download a copy from the wib, edit and upload back to the wib.

Edit yml on WIB
---------------
```
ssh root@192.168.121.1
cd /etc/cryo/yml
```

edit templates/room.yml or templates/cold.yml
then generate yml files for all ASICs

```
cd /etc/cryo/yml
cryo_yml templates/room.yml wib_cryo_config_ASIC_ExtClk_RoomTemp
cryo_yml templates/cold.yml wib_cryo_config_ASIC_ExtClk_ColdTemp

sync;sync;sync
```

Edit yml on host
----------------
```
mkdir tmp_yml
rsync -avchP root@192.168.121.1:/etc/cryo/yml/ tmp_yml/
```

edit templates/room.yml or templates/cold.yml
then generate yml files for all ASICs

```
cd tmp_yml
cryo_yml templates/room.yml wib_cryo_config_ASIC_ExtClk_RoomTemp
cryo_yml templates/cold.yml wib_cryo_config_ASIC_ExtClk_ColdTemp
```

upload to the wib
```
cd ../
rsync -avchP tmp_yml/ root@192.168.121.1:/etc/cryo/yml/
```

Some Tips
---------
- `templates/room.yml` is the room temperature setting for ASIC0 
- similarly `templates/cold.yml` for cold setting
- for the `rsync` command
  remember to put `/` at the end of the source and target folder
- to check what you have edited, do `diff templates/room.yml wib_cryo_config_ASIC_ExtClk_RoomTemp_asic0.yml` before running `cryo-yml`
- notify on the slack channel when there is a new stable version
