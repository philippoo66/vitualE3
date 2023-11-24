# vitualE3
virtual E3 device for testing in conjunction with open3e

- place virtualE3.py and virtdyndata.py in the same directory where Open3E is located. 
- run Open3E_depictSystem.py with option `writesimul=True`.

Afterwards you have a complete snapshot of your E3 system and you can work with Open3E on this instead of your real device/s. Best to use virtual CAN bus vcan0 instead of can0 with both virtualE3 and Open3Eclient.

Utilizing virtdyndata.py and command line option `-dyn` you can have randomly changing values within set ranges for DIDs configured as dyn.

Use

    python3 virtualE3.py -cnfg dev

to run virtualE3 utilizing configuration built by Open3E_depictSystem. (dev = shortcut for devices.json)

# Usage

    python3 virtualE3.py [-h] [-c CAN] [-dev DEV] [-a] [-addr ADDR] [-cnfg CONFIG]

    arguments:
    -h, --help            show this help message and exit
    -c CAN, --can CAN     use can device, e.g. can0
    -dev DEV, --dev DEV   boiler type --dev vdens or --dev vcal or --dev vx3 or
                        --dev vair (ignored when -cnfg is set)
    -old, --old           -old for not universal list
    -dyn, --dyn           -dyn for dynamic values
    -a, --all             respond to all COB-IDs
    -addr ADDR, --addr ADDR
                        ECU address
    -cnfg CONFIG, --config CONFIG
                        json configuration file of Open3E

