# vitualE3
virtual E3 device for testing reading and writing DIDs in conjunction with [open3e](https://github.com/abnoname/open3e) or other communication tools.

- place virtualE3.py and virtdyndata.py in the same directory where Open3E is located (multiple files are shared).
- run Open3E_depictSystem.py with command line option -s (--simul) set.

Afterwards you have a complete snapshot of your E3 system and using virtualE3 you can work with Open3E on this instead of your real device/s. Best to use virtual CAN bus vcan0 instead of can0 with both virtualE3 and Open3Eclient.

Utilizing virtdyndata.py and command line option `-dyn` you can have randomly changing values within set ranges for DIDs configured as dyn.

Use

    python3 virtualE3.py -cnfg dev

to run virtualE3 utilizing configuration built by Open3E_depictSystem. (dev is programmed shortcut for devices.json)

# Usage

    python3 virtualE3.py [-h] [-c CAN] [-dev DEV] [-old] [-dyn] [-a] [-addr ADDR] [-cnfg CONFIG]

    arguments:
    -h, --help            show this help message and exit
    -c CAN, --can CAN     use can device, e.g. vcan0 (default)
    -dev DEV, --dev DEV   boiler type --dev vdens or --dev vcal or --dev vx3 or
                        --dev vair or _680 or _6A1 or ... (ignored when -cnfg is set)
    -old, --old           -old for not universal list
    -dyn, --dyn           -dyn for dynamic values (virtdyndata.py required configured)
    -a, --all             respond to all COB-IDs
    -addr ADDR, --addr ADDR
                        ECU address (default 0x680)
    -cnfg CONFIG, --config CONFIG
                        json configuration file of Open3E (dev short for devices.json)

# Requirements

https://pypi.org/project/python-can/

## Virtual CAN Interface

check https://netmodule-linux.readthedocs.io/en/latest/howto/can.html - "Virtual CAN Interface - vcan"

in general (often root privileges required, add a leading 'sudo' in case)

load vcan module if not loaded:

    modprobe vcan

create vcan0 interface

    ip link add dev vcan0 type vcan
    ip link set vcan0 mtu 16
    ip link set up vcan0

