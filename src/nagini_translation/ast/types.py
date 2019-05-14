"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from typing import Optional, List

from nagini_translation.ast import names


class VyperType:

    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return self.name

    
class FunctionType(VyperType):

    def __init__(self, arg_types: List[VyperType], return_type: Optional[VyperType]):
        self.arg_types = arg_types
        self.return_type = return_type
        name = f'({", ".join(str(arg_types))}) -> {return_type}'
        super().__init__(name)


class MapType(VyperType):

    def __init__(self, key_type: VyperType, value_type: VyperType):
        self.key_type = key_type
        self.value_type = value_type
        name = f'{names.MAP}({key_type}, {value_type})'
        super().__init__(name)


class ArrayType(VyperType):

    def __init__(self, element_type: VyperType, size: int, is_strict: bool = True):
        self.element_type = element_type
        self.size = size
        self.is_strict = is_strict
        name = f'{element_type}[{size}]'
        super().__init__(name)


class PrimitiveType(VyperType):

    def __init__(self, name: str):
        super().__init__(name)


VYPER_BOOL = PrimitiveType(names.BOOL)
VYPER_WEI_VALUE = PrimitiveType(names.WEI_VALUE)
VYPER_TIME = PrimitiveType(names.TIMESTAMP)
VYPER_INT128 = PrimitiveType(names.INT128)
VYPER_UINT256 = PrimitiveType(names.UINT256)
VYPER_ADDRESS = PrimitiveType(names.ADDRESS)
VYPER_BYTE = PrimitiveType(names.BYTE)

TYPES = {
    VYPER_BOOL.name: VYPER_BOOL,
    VYPER_WEI_VALUE.name: VYPER_WEI_VALUE,
    VYPER_INT128.name: VYPER_INT128,
    VYPER_UINT256.name: VYPER_UINT256,
    VYPER_ADDRESS.name: VYPER_ADDRESS,
    VYPER_BYTE.name: VYPER_BYTE,
    names.TIMESTAMP: VYPER_TIME,
    names.TIMEDELTA: VYPER_TIME
}


def is_unsigned(type: VyperType) -> bool:
    return type == VYPER_UINT256 or type == VYPER_WEI_VALUE or type == VYPER_TIME


def has_strict_array_size(element_type: VyperType) -> bool:
    return element_type != VYPER_BYTE


class TypeBuilder(ast.NodeVisitor):

    def build(self, node) -> VyperType:
        return self.visit(node)

    def generic_visit(self, node):
        assert False # TODO: handle

    def visit_Name(self, node: ast.Name) -> VyperType:
        return TYPES[node.id]

    def visit_Call(self, node: ast.Call) -> VyperType:
        # We allow public and map, constant should already be replaced
        if node.func.id == names.PUBLIC:
            return self.visit(node.args[0])
        elif node.func.id == names.MAP:
            key_type = self.visit(node.args[0])
            value_type = self.visit(node.args[1])
            return MapType(key_type, value_type)
        else:
            assert False # TODO handle

    def visit_Subscript(self, node: ast.Subscript) -> VyperType:
        element_type = self.visit(node.value)
        # Array size has to be an int or a constant 
        # (which has already been replaced by an int)
        size = node.slice.value.n
        return ArrayType(element_type, size, has_strict_array_size(element_type))
