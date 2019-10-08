"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from typing import Optional, List, Dict

from nagini_translation.utils import NodeVisitor
from nagini_translation.ast import names
from nagini_translation.exceptions import UnsupportedException


class VyperType:

    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return self.name


class FunctionType(VyperType):

    def __init__(self, arg_types: List[VyperType], return_type: Optional[VyperType]):
        self.arg_types = arg_types
        self.return_type = return_type
        arg_type_names = [str(arg) for arg in arg_types]
        name = f'({", ".join(arg_type_names)}) -> {return_type}'
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


class StructType(VyperType):

    def __init__(self, name: str, member_types: Dict[str, VyperType]):
        self.member_types = member_types
        self.member_indices = {k: i for i, k in enumerate(member_types)}
        super().__init__(name)

    def add_member(self, name: str, type: VyperType):
        self.member_types[name] = type
        self.member_indices[name] = len(self.member_indices)


class ContractType(VyperType):

    def __init__(self, name: str, function_types: Dict[str, FunctionType]):
        self.name = name
        self.function_types = function_types


class StringType(ArrayType):

    def __init__(self, size: int):
        super().__init__(VYPER_BYTE, size, False)
        self.name = f'{names.STRING}[{size}]'


class PrimitiveType(VyperType):

    def __init__(self, name: str):
        super().__init__(name)


class DecimalType(PrimitiveType):

    def __init__(self, name: str, digits: int):
        super().__init__(name)
        self.scaling_factor = pow(10, digits)


class EventType(VyperType):

    def __init__(self, arg_types: List[VyperType]):
        self.arg_types = arg_types
        arg_type_names = [str(arg) for arg in arg_types]
        super().__init__(f'event({", ".join(arg_type_names)})')


VYPER_BOOL = PrimitiveType(names.BOOL)
VYPER_INT128 = PrimitiveType(names.INT128)
VYPER_UINT256 = PrimitiveType(names.UINT256)
VYPER_DECIMAL = DecimalType(names.DECIMAL, 10)
VYPER_WEI_VALUE = VYPER_UINT256
VYPER_ADDRESS = PrimitiveType(names.ADDRESS)
VYPER_BYTE = PrimitiveType(names.BYTE)
VYPER_BYTES32 = ArrayType(VYPER_BYTE, 32, True)

TYPES = {
    VYPER_BOOL.name: VYPER_BOOL,
    VYPER_WEI_VALUE.name: VYPER_WEI_VALUE,
    VYPER_INT128.name: VYPER_INT128,
    VYPER_UINT256.name: VYPER_UINT256,
    VYPER_DECIMAL.name: VYPER_DECIMAL,
    names.WEI_VALUE: VYPER_WEI_VALUE,
    VYPER_ADDRESS.name: VYPER_ADDRESS,
    VYPER_BYTE.name: VYPER_BYTE,
    names.BYTES32: VYPER_BYTES32,
    names.STRING: VYPER_BYTE,
    names.TIMESTAMP: VYPER_UINT256,
    names.TIMEDELTA: VYPER_UINT256
}

MSG_TYPE = StructType(names.MSG, {
    names.MSG_SENDER: VYPER_ADDRESS,
    names.MSG_VALUE: VYPER_WEI_VALUE,
    names.MSG_GAS: VYPER_UINT256
})

BLOCK_TYPE = StructType(names.BLOCK, {
    names.BLOCK_COINBASE: VYPER_ADDRESS,
    names.BLOCK_DIFFICULTY: VYPER_UINT256,
    names.BLOCK_NUMBER: VYPER_UINT256,
    names.BLOCK_PREVHASH: VYPER_BYTES32,
    names.BLOCK_TIMESTAMP: VYPER_UINT256
})

TX_TYPE = StructType(names.TX, {
    names.TX_ORIGIN: VYPER_ADDRESS
})


def is_unsigned(type: VyperType) -> bool:
    return type == VYPER_UINT256


def has_strict_array_size(element_type: VyperType) -> bool:
    return element_type != VYPER_BYTE


class TypeBuilder(NodeVisitor):

    def __init__(self, type_map: Dict[str, VyperType]):
        self.type_map = type_map

    def build(self, node) -> VyperType:
        return self.visit(node)

    @property
    def method_name(self):
        return '_visit'

    def generic_visit(self, node):
        raise UnsupportedException(node)

    def _visit_Name(self, node: ast.Name) -> VyperType:
        return self.type_map.get(node.id) or TYPES[node.id]

    def _visit_ClassDef(self, node: ast.ClassDef) -> VyperType:
        assert node.body

        # This is a struct
        if isinstance(node.body[0], ast.AnnAssign):
            members = {n.target.id: self.visit(n.annotation) for n in node.body}
            return StructType(node.name, members)
        # This is a contract
        elif isinstance(node.body[0], ast.FunctionDef):
            functions = {}
            for f in node.body:
                name = f.name
                arg_types = [self.visit(arg.annotation) for arg in f.args.args]
                return_type = None if f.returns is None else self.visit(f.returns)
                functions[name] = FunctionType(arg_types, return_type)
            return ContractType(node.name, functions)
        else:
            assert False

    def _visit_Call(self, node: ast.Call) -> VyperType:
        # We allow
        #   - public, indexed: not important for verification
        #   - map: map type
        #   - event: event type
        # Not allowed is
        #   - constant: should already be replaced
        # Anything else is treated as a unit
        if node.func.id == names.PUBLIC or node.func.id == names.INDEXED:
            return self.visit(node.args[0])
        elif node.func.id == names.MAP:
            key_type = self.visit(node.args[0])
            value_type = self.visit(node.args[1])
            return MapType(key_type, value_type)
        elif node.func.id == names.EVENT:
            dict_literal = node.args[0]
            arg_types = [self.visit(arg) for arg in dict_literal.values]
            return EventType(arg_types)
        else:
            return TYPES[node.func.id]

    def _visit_Subscript(self, node: ast.Subscript) -> VyperType:
        element_type = self.visit(node.value)
        # Array size has to be an int or a constant
        # (which has already been replaced by an int)
        size = node.slice.value.n
        return ArrayType(element_type, size, has_strict_array_size(element_type))
