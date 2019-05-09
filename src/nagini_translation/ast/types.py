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


class MapType(VyperType):

    def __init__(self, key_type: VyperType, value_type: VyperType):
        self.key_type = key_type
        self.value_type = value_type
        name = f'{names.MAP}({key_type}, {value_type})'
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


VYPER_BOOL = PrimitiveType(names.BOOL)
VYPER_WEI_VALUE = PrimitiveType(names.WEI_VALUE)
VYPER_INT128 = PrimitiveType(names.INT128)
VYPER_UINT256 = PrimitiveType(names.UINT256)
VYPER_ADDRESS = PrimitiveType(names.ADDRESS)

TYPES = {
    VYPER_BOOL.name: VYPER_BOOL,
    VYPER_WEI_VALUE.name: VYPER_WEI_VALUE,
    VYPER_INT128.name: VYPER_INT128,
    VYPER_UINT256.name: VYPER_UINT256,
    VYPER_ADDRESS.name: VYPER_ADDRESS
}


def is_unsigned(type: VyperType) -> bool:
    return type == VYPER_UINT256 or type == VYPER_WEI_VALUE


class TypeContext:

    def __init__(self, type: VyperType, is_public: bool):
        self.type = type
        self.is_public = is_public


class TypeBuilder(ast.NodeVisitor):

    def build(self, node) -> TypeContext:
        return self.visit(node)

    def generic_visit(self, node):
        assert False # TODO: handle

    def visit_Name(self, node: ast.Name) -> TypeContext:
        return TypeContext(TYPES[node.id], False)

    def visit_Call(self, node: ast.Call) -> TypeContext:
        # We allow public and map, constant should already be replaced
        if node.func.id == names.PUBLIC:
            ctx = self.visit(node.args[0])
            ctx.is_public = True
        elif node.func.id == names.MAP:
            key_type_ctx = self.visit(node.args[0])
            value_type_ctx = self.visit(node.args[1])
            type = MapType(key_type_ctx.type, value_type_ctx.type)
            ctx = TypeContext(type, False)
        else:
            assert False # TODO handle

        return ctx

    def visit_Subscript(self, node: ast.Subscript) -> TypeContext:
        ctx = self.visit(node.value)
        # Array size has to be an int or a constant 
        # (which has already been replaced by an int)
        size = node.slice.value.n
        ctx.type = ArrayType(ctx.type, size)
        return ctx