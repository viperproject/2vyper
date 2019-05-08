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

    def __str__(self) -> str:
        return self.name


class MapType(VyperType):

    def __init__(self, key_type: VyperType, value_type: VyperType):
        self.key_type = key_type
        self.value_type = value_type
        name = f'map({key_type}, {value_type})'
        super().__init__(name)


class ArrayType(VyperType):

    def __init__(self, element_type: VyperType, size: int):
        self.element_type = element_type
        self.size = size
        name = f'{element_type}[{size}]'
        super().__init__(name)


class PrimitiveType(VyperType):

    def __init__(self, name: str):
        super().__init__(name)


VYPER_BOOL = PrimitiveType('bool')
VYPER_WEI_VALUE = PrimitiveType('wei_value')
VYPER_INT128 = PrimitiveType('int128')
VYPER_UINT256 = PrimitiveType('uint256')
VYPER_ADDRESS = PrimitiveType('address')

TYPES = {
    VYPER_BOOL.name: VYPER_BOOL,
    VYPER_WEI_VALUE.name: VYPER_WEI_VALUE,
    VYPER_INT128.name: VYPER_INT128,
    VYPER_UINT256.name: VYPER_UINT256,
    VYPER_ADDRESS.name: VYPER_ADDRESS
}


def is_unsigned(type: VyperType) -> bool:
    return type == VYPER_UINT256 or type == VYPER_WEI_VALUE