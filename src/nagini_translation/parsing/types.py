"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Optional, List


class VyperType:

    def __init__(self, name: str):
        self.name = name


class PrimitiveType(VyperType):

    def __init__(self, name: str, default_value: str):
        VyperType.__init__(self, name)
        self.default_value = default_value


VYPER_BOOL = PrimitiveType('bool', 'False')
VYPER_WEI_VALUE = PrimitiveType('wei_value', '0')
VYPER_INT128 = PrimitiveType('int128', '0')
VYPER_UINT256 = PrimitiveType('uint256', '0')
VYPER_ADDRESS = PrimitiveType('address', '0')

TYPES = {
    VYPER_BOOL.name: VYPER_BOOL,
    VYPER_WEI_VALUE.name: VYPER_WEI_VALUE,
    VYPER_INT128.name: VYPER_INT128,
    VYPER_UINT256.name: VYPER_UINT256,
    VYPER_ADDRESS.name: VYPER_ADDRESS
}