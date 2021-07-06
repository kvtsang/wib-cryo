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

Start rogue gui on host
-----------------------
python -m pyrogue --server=192.168.121.1:9099 gui &

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

Disable Lane (Experimental)
===========================

This example shows how to disable an unlocked lane #0 from FEMB #1.
```
wib_cryo.py toggle_sr0
wib_cryo.py disable_lane --femb 1 --lane 0 --val 0x390
wib_rx_mask.py 0xff1f
```

**Notes**
- `toogle_sr0` is required only if any one of the lanes is not locked
  - the locked status might change after `toggle_sr0`
- `disable_lane` zeroes out all channels on the disabled lane using `WritePixelData`
  - the active channels are configured with `--val`
  - DO NOT execute `config_asic` or `WriteColData` after `disable_lane`
- `rx_mask` is a 16-bit number (4 FEMBs x 4 lanes) to control data stream
  - 0: unmasked, 1: masked (inactive lane)
  - `disable_lane` gives a suggested `rx_mask` for one FEMB with disabled lane(s)
  - for multiple FEMBs setup, you'll need to merge several masks
  - the `rx_mask` only ignore the valid bit of the data link without zeroing out
  - the masked data are unsynchronized w/ the normal data

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

Start rogue gui on host
=======================
python -m pyrogue --server=192.168.121.1:9099 gui &

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

Spy Buffer Data Plots
=====================

Assume series of runs (dataset) are recorded in "/home/wib/data/SN03/Cold/T2".
The following command output psd and pulse plots to `{YYYY-MM-DD}_WIB_FEMB_SN03_T2_Cold`.
```
wib_plot2 /home/wib/data/SN03/Cold/T2
```

**Notes**
- the folder and file naming are crucial
- make sure to following the folder structure 
  `something/SN{01,02,03}/{Room,Cold}/T{1,2,3,4,..}`
- ASIC setting (e.g. `0x390`) should be part of data folder name
  refer to `wib_daq.py -o <output>`

A good example should look like this
```
$ ls /home/wib/data/SN03/Cold/T2 

WIB_0x390  WIB_0x391  WIB_0x394  WIB_0x395  WIB_0x398  WIB_0x399  WIB_0x39c  WIB_0x39d
```

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
