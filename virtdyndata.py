""" 
dyndata = { did : [ [start, len, type], ...], ... }
    types:
        'F' : full range 0x00..0xff
        'N' : number, 0..9
        'L' : letter upper case 
        'l' : letter lower case
        [min,max] : min to max 
        else : printable ascii 0x20..0x7E
"""

dyndata = {
    #257 : [[0, 1, [1,10]], [1, 1, [0,0]], [2, 120, [0x01,0x01]]],
    #264 : [[0, 1, [1,10]], [1, 1, [0,0]], [2, 2, 'F'], [4, 120, [0x01,0x01]]],
    268 : [[0, 1, 'F'], [6, 1, [0x40,0xB0]]],  # FlowTemperatureSensor: actual, average: lsb
}