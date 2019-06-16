#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

bb: bytes32


@public
def get_bytes() -> bytes32:
    return self.bb


@public
def set_bytes(new_bytes: bytes32):
    self.bb = new_bytes