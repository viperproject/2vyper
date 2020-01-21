"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Optional, List, Dict

from twovyper.ast import ast_nodes as ast, names
from twovyper.ast.visitors import NodeVisitor

from twovyper.exceptions import InvalidProgramException


class VyperType:

    def __init__(self, id: str):
        self.id = id

    def __str__(self) -> str:
        return self.id

    def __eq__(self, other) -> bool:
        if isinstance(other, VyperType):
            return self.id == other.id

        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.id)


class FunctionType(VyperType):

    def __init__(self, arg_types: List[VyperType], return_type: Optional[VyperType]):
        self.arg_types = arg_types
        self.return_type = return_type
        arg_type_names = [str(arg) for arg in arg_types]
        id = f'({", ".join(arg_type_names)}) -> {return_type}'
        super().__init__(id)


class MapType(VyperType):

    def __init__(self, key_type: VyperType, value_type: VyperType):
        self.key_type = key_type
        self.value_type = value_type
        id = f'{names.MAP}({key_type}, {value_type})'
        super().__init__(id)


class ArrayType(VyperType):

    def __init__(self, element_type: VyperType, size: int, is_strict: bool = True):
        self.element_type = element_type
        self.size = size
        self.is_strict = is_strict
        id = f'{element_type}[{"" if is_strict else "<="}{size}]'
        super().__init__(id)


class StructType(VyperType):

    def __init__(self, name: str, member_types: Dict[str, VyperType]):
        id = f'struct {name}'
        super().__init__(id)
        self.name = name
        self.member_types = member_types
        self.member_indices = {k: i for i, k in enumerate(member_types)}

    def add_member(self, name: str, type: VyperType):
        self.member_types[name] = type
        self.member_indices[name] = len(self.member_indices)


class AnyStructType(VyperType):

    def __init__(self):
        super().__init__('$AnyStruct')


class AnyAddressType(StructType):

    def __init__(self, name: str, member_types: Dict[str, VyperType]):
        assert names.ADDRESS_BALANCE not in member_types
        assert names.ADDRESS_CODESIZE not in member_types
        assert names.ADDRESS_IS_CONTRACT not in member_types

        member_types[names.ADDRESS_BALANCE] = VYPER_WEI_VALUE
        member_types[names.ADDRESS_CODESIZE] = VYPER_INT128
        member_types[names.ADDRESS_IS_CONTRACT] = VYPER_BOOL
        super().__init__(name, member_types)


class AddressType(AnyAddressType):

    def __init__(self):
        super().__init__(names.ADDRESS, {})


class SelfType(AnyAddressType):

    def __init__(self, member_types: Dict[str, VyperType]):
        super().__init__(names.SELF, member_types)


class ContractType(VyperType):

    def __init__(self,
                 name: str,
                 function_types: Dict[str, FunctionType],
                 function_modifiers: Dict[str, str]):
        id = f'contract {name}'
        super().__init__(id)
        self.name = name
        self.function_types = function_types
        self.function_modifiers = function_modifiers


class InterfaceType(VyperType):

    def __init__(self, name: str):
        id = f'interface {name}'
        super().__init__(id)
        self.name = name


class StringType(ArrayType):

    def __init__(self, size: int):
        super().__init__(VYPER_BYTE, size, False)
        self.id = f'{names.STRING}[{size}]'


class PrimitiveType(VyperType):

    def __init__(self, name: str):
        super().__init__(name)
        self.name = name


class BoundedType(PrimitiveType):

    def __init__(self, name: str, lower: int, upper: int):
        super().__init__(name)
        self.lower = lower
        self.upper = upper


class DecimalType(BoundedType):

    def __init__(self, name: str, digits: int, lower: int, upper: int):
        self.number_of_digits = digits
        self.scaling_factor = 10 ** digits
        lower *= self.scaling_factor
        upper *= self.scaling_factor
        super().__init__(name, lower, upper)


class EventType(VyperType):

    def __init__(self, arg_types: List[VyperType]):
        arg_type_names = [str(arg) for arg in arg_types]
        id = f'event({", ".join(arg_type_names)})'
        super().__init__(id)
        self.arg_types = arg_types


VYPER_BOOL = PrimitiveType(names.BOOL)
VYPER_INT128 = BoundedType(names.INT128, -2 ** 127, 2 ** 127 - 1)
VYPER_UINT256 = BoundedType(names.UINT256, 0, 2 ** 256 - 1)
VYPER_DECIMAL = DecimalType(names.DECIMAL, 10, -2 ** 127, 2 ** 127 - 1)
VYPER_WEI_VALUE = VYPER_UINT256
VYPER_ADDRESS = BoundedType(names.ADDRESS, 0, 2 ** 160 - 1)
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

CHAIN_TYPE = StructType(names.CHAIN, {
    names.CHAIN_ID: VYPER_UINT256
})

TX_TYPE = StructType(names.TX, {
    names.TX_ORIGIN: VYPER_ADDRESS
})


def is_numeric(type: VyperType) -> bool:
    return type in [VYPER_INT128, VYPER_UINT256, VYPER_DECIMAL]


def is_bounded(type: VyperType) -> bool:
    return type in [VYPER_INT128, VYPER_UINT256, VYPER_DECIMAL, VYPER_ADDRESS]


def is_integer(type: VyperType) -> bool:
    return type == VYPER_INT128 or type == VYPER_UINT256


def is_unsigned(type: VyperType) -> bool:
    return type == VYPER_UINT256 or type == VYPER_ADDRESS


def has_strict_array_size(element_type: VyperType) -> bool:
    return element_type != VYPER_BYTE


def is_bytes_array(type: VyperType):
    return isinstance(type, ArrayType) and type.element_type == VYPER_BYTE


def matches(t, m):
    """
    Determines whether a type t matches a required type m in the
    specifications.
    Usually the types have to be the same, except non-strict arrays
    which may be shorter than the expected length, and contract types
    which can be used as addresses. Also, all integer types are treated
    as mathematical integers.
    """

    a1 = isinstance(t, ArrayType)
    a2 = isinstance(m, ArrayType) and not m.is_strict
    if a1 and a2 and t.element_type == m.element_type:
        return t.size <= m.size
    elif is_integer(t) and is_integer(m):
        return True
    elif isinstance(t, ContractType) and m == VYPER_ADDRESS:
        return True
    elif isinstance(t, InterfaceType) and m == VYPER_ADDRESS:
        return True
    else:
        return t == m


class TypeBuilder(NodeVisitor):

    def __init__(self, type_map: Dict[str, VyperType]):
        self.type_map = type_map

    def build(self, node) -> VyperType:
        return self.visit(node)

    @property
    def method_name(self):
        return '_visit'

    def generic_visit(self, node):
        raise InvalidProgramException(node, 'invalid.type')

    def _visit_Name(self, node: ast.Name) -> VyperType:
        type = self.type_map.get(node.id) or TYPES.get(node.id)
        if type is None:
            raise InvalidProgramException(node, 'invalid.type')
        return type

    def _visit_StructDef(self, node: ast.StructDef) -> VyperType:
        members = {n.target.id: self.visit(n.annotation) for n in node.body}
        return StructType(node.name, members)

    def _visit_ContractDef(self, node: ast.ContractDef) -> VyperType:
        functions = {}
        modifiers = {}
        for f in node.body:
            name = f.name
            arg_types = [self.visit(arg.annotation) for arg in f.args]
            return_type = None if f.returns is None else self.visit(f.returns)
            functions[name] = FunctionType(arg_types, return_type)
            modifiers[name] = f.body[0].value.id
        return ContractType(node.name, functions, modifiers)

    def _visit_FunctionCall(self, node: ast.FunctionCall) -> VyperType:
        # We allow
        #   - public, indexed: not important for verification
        #   - map: map type
        #   - event: event type
        # Not allowed is
        #   - constant: should already be replaced
        # Anything else is treated as a unit
        if node.name == names.PUBLIC or node.name == names.INDEXED:
            return self.visit(node.args[0])
        elif node.name == names.MAP:
            key_type = self.visit(node.args[0])
            value_type = self.visit(node.args[1])
            return MapType(key_type, value_type)
        elif node.name == names.EVENT:
            dict_literal = node.args[0]
            arg_types = [self.visit(arg) for arg in dict_literal.values]
            return EventType(arg_types)
        else:
            type = self.type_map.get(node.name) or TYPES.get(node.name)
            if type is None:
                raise InvalidProgramException(node, 'invalid.type')
            return type

    def _visit_Subscript(self, node: ast.Subscript) -> VyperType:
        element_type = self.visit(node.value)
        # Array size has to be an int or a constant
        # (which has already been replaced by an int)
        size = node.index.n
        return ArrayType(element_type, size, has_strict_array_size(element_type))
