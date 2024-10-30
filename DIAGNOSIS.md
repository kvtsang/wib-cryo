Diagnosis of CRYO Data
======================

The script `kcu_plot` produces a set of standard diagnosis plots
(mean, std, spectral density) for CRYO data taken at SLAC setup.

Setup
-----
The following examples assume running the script on `pc98921`.

To access the pre-installed python environment, 
```
source /home/cryo/setup.sh
```
in a fresh terminal.

Naming Convention
-----------------
The script is tailored for the SLAC setup. 
File naming convention is enforced strictly.
Other settings, other than specified below, do not work properly.

The folder structure should be like `FEMB_SN03/Room/T1_suffix`, where  
- `FEMB_SN03` : serial number of the board being tested
- `Room` : testing condition, either `Room` or `Cold`
- `T1` : dataset in sequence `T1`, `T2`, `T3`, ...
- `_suffix` (optional) : additional info about the dataset, like `T1_CTS_noToyTPC_blcoarse3`, if desired.

The file names must contains the configuration bits (in hex format) and in `.dat` extension for raw data format.
```
FEMB_0x390.dat
FEMB_0x391.dat
FEMB_0x394.dat
FEMB_0x395.dat
FEMB_0x398.dat
FEMB_0x399.dat
FEMB_0x39c.dat
FEMB_0x39d.dat
```
The prefix `FEMB_` can be changed and additional info can be appened (e.g. `FEMB_0x390_something.dat`).
However the bits `0x390`, `0x391`, ... must be presented and no other settings are allowed.

Raw to HDF5
-----------
The conversion script for accessing raw data file is modified from `slaclab/epix` project.
It may be subjected to change for future versions. This script was tested on July 2024.
Please contact the original authors (SLAC-TID) for further assistance.

To convert raw data file:
```
convert-raw.py DATA_DIR/FEMB_0x390.dat
```
An output file `FEMB_0x390.hdf5` is saved under `DATA_DIR`, the same directory as the `dat` file.

To process multiple files in the same directory:
```
for f in _DATA_DIR_/*.dat; do convert-raw.py $f;done
```

Plotting
--------
Prerequisite: a series of eight hdf5 files with correct naming convention in the same directory, e.g.

```
> ls FEMB_SN03/Room/T1

FEMB_0x390.hdf5
FEMB_0x391.hdf5
FEMB_0x394.hdf5
FEMB_0x395.hdf5
FEMB_0x398.hdf5
FEMB_0x399.hdf5
FEMB_0x39c.hdf5
FEMB_0x39d.hdf5
```

To make diagnostic plots:
```
kcu_plot -1 _DATA_DIR_/FEMB_SN03/Room/T1
```
The figures are saved in a new directory (e.g. `2024-07-10_KCU_FEMB_FEMB_SN03_T1_Room`) under where the script is executed.

Here are the list of plotting options:
```
> kcu_plot

Make plots for dataset taken by KCU system.

Usage: kcu_plot -1|-2 <directory> [title]
  
  -1, -2
    Run at half speed (-1) or full speed (-2).

  directory
    Input directory for hdf5 files.
  
  title 
    Title for figures and output file names, optional.
```

- use `-2` if the data are taken in full speed
- for custom figure titles, `kcu_plot -1 DATA_DIR "my title"`
