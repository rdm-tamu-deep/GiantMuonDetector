from picosdk.ps2000 import ps2000 as ps
unit_location_dict = {
    "left_bottom": b"JY214/1608",
    "right_bottom": b"JY214/1781",
}
def get_units():
    '''finds units and sorts them into a dict for ease of initilization and matching with location'''
    units = ps.list_units()
    print("{} units found".format(len(units)))
    #match unit with location
    for unit in units:
        serial = unit.serial
        for k,v in unit_location_dict.items():
            if v == serial: break
        if v == serial: unit_location_dict[k] = unit
        else: print("unit {} not matched".format(serial))
    return unit_location_dict