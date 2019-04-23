"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from nagini_translation.parsing.transformer import transform
from nagini_translation.parsing.types import VyperType
from nagini_translation.parsing.types import TYPES, VYPER_INT128
from nagini_translation.parsing.ast import VyperProgram, VyperFunction, VyperVar


def parse(contract: str) -> VyperProgram:
    contract_ast = ast.parse(contract)
    contract_ast = transform(contract_ast)
    program_builder = ProgramBuilder()
    return program_builder.build(contract_ast)


class ProgramBuilder(ast.NodeVisitor):

    def __init__(self):
        self.state = {}
        self.functions = {}

        self.type_builder = TypeBuilder()

    def build(self, node) -> VyperProgram:
        self.visit(node)
        return VyperProgram(self.state, self.functions)

    def visit_AnnAssign(self, node):
        ctx = self.type_builder.build(node.annotation)
        variable_name = node.target.id
        variable_type = ctx.type
        var = VyperVar(variable_name, variable_type, node)
        self.state[variable_name] = var

    def visit_FunctionDef(self, node):
        local = LocalProgramBuilder()
        args, local_vars = local.build(node)
        return_type = None if node.returns is None else self.type_builder.build(node.returns).type
        function = VyperFunction(node.name, args, local_vars, return_type, node)
        self.functions[node.name] = function


class LocalProgramBuilder(ast.NodeVisitor):

    def __init__(self):
        self.args = {}
        self.local_vars = {}

        self.type_builder = TypeBuilder()
    
    def build(self, node):
        self.visit(node)
        return self.args, self.local_vars

    def visit_arg(self, node):
        arg_name = node.arg
        arg_type = self.type_builder.build(node.annotation).type
        var = VyperVar(arg_name, arg_type, node)
        self.args[arg_name] = var

    def visit_AnnAssign(self, node):
        variable_name = node.target.id
        variable_type = self.type_builder.build(node.annotation).type
        var = VyperVar(variable_name, variable_type, node)
        self.local_vars[variable_name] = var

    def visit_For(self, node):
        variable_name = node.target.id
        variable_type = VYPER_INT128
        var = VyperVar(variable_name, variable_type, node)
        self.local_vars[variable_name] = var
        self.generic_visit(node)


class TypeContext:

    def __init__(self, type: VyperType, is_constant: bool, is_public: bool):
        self.type = type
        self.is_public = is_public


class TypeBuilder(ast.NodeVisitor):

    def build(self, node) -> TypeContext:
        return self.visit(node)

    def generic_visit(self, node):
        raise AssertionError("Complex types not yet supported.")

    def visit_Name(self, node: ast.Name) -> TypeContext:
        return TypeContext(TYPES[node.id], False, False)

    def visit_Call(self, node: ast.Call) -> TypeContext:
        # TODO: make work for maps
        ctx = self.visit(node.args[0])
        
        if node.func.id == 'public':
            ctx.is_public = True

        return ctx

