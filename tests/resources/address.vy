
owner: address

@public
def set_owner(a: address) -> address:
    b: address = a
    b = a
    return b

@public
def compare_addresses(a: address, b: address) -> address:
    if a == b:
        return a
    else:
        return b

@public
def lit():
    a: address = 0x0000000000000000000000000000000000000000
    b: address = 0x000000001000000000010000000000000600000a