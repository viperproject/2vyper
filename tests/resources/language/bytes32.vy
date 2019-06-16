
bb: bytes32


@public
def get_bytes() -> bytes32:
    return self.bb


@public
def set_bytes(new_bytes: bytes32):
    self.bb = new_bytes