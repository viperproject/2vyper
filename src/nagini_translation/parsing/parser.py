"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from typing import List

from nagini_translation.parsing.preprocessor import preprocess
from nagini_translation.parsing.transformer import transform

from nagini_translation.ast.nodes import VyperProgram, VyperFunction, VyperVar
from nagini_translation.ast.types import VyperType, MapType
from nagini_translation.ast.types import TYPES, VYPER_INT128

from nagini_translation.errors.translation_exceptions import UnsupportedException, InvalidProgramException


def parse(contract: str, filename: str) -> VyperProgram:
    contract = preprocess(contract)
    contract_ast = ast.parse(contract, filename)
    contract_ast = transform(contract_ast)
    program_builder = ProgramBuilder()
    return program_builder.build(contract_ast)


class ProgramBuilder(ast.NodeVisitor):
    """
    The program builder creates a Vyper program out of the AST. It collects contract 
    state variables and functions. It should only be used by calling the build method once.
    """

    # Pre and postconditions are only allowed before a function. As we walk through all
    # top-level statements we gather pre and postconditions until we reach a function
    # definition.

    def __init__(self):
        self.state = {}
        self.functions = {}
        self.invariants = []

        self.preconditions = []
        self.postconditions = []

        self.type_builder = TypeBuilder()

    def build(self, node) -> VyperProgram:
        self.visit(node)
        # No trailing pre and postconditions allowed
        self._check_no_prepostconditions()
        return VyperProgram(self.state, self.functions, self.invariants)
    
    def _check_no_prepostconditions(self):
        if self.preconditions:
            cond = "Precondition"
            node = self.preconditions[0]
        elif self.postconditions:
            cond = "Postcondition"
            node = self.postconditions[0]
        else:
            return
        raise InvalidProgramException(node, f"{cond} only allowed before function")

    def visit_AnnAssign(self, node):
        # No preconditions and postconditions are allowed before contract state variables
        self._check_no_prepostconditions()

        ctx = self.type_builder.build(node.annotation)
        variable_name = node.target.id
        variable_type = ctx.type
        var = VyperVar(variable_name, variable_type, node)
        self.state[variable_name] = var

    def visit_Assign(self, node):
        # This is for invariants and pre/postconditions which get translated to
        # assignments during preprocessing.

        if not len(node.targets) == 1:
            raise AssertionError("Contracts should only have a single target.")
        if not isinstance(node.targets[0], ast.Name):
            raise AssertionError("The target of a contract should be a name.")
        
        name = node.targets[0].id
        if name == 'invariant':
            # No preconditions and posconditions allowed before invariants
            self._check_no_prepostconditions()

            self.invariants.append(node.value)
        elif name == 'requires':
            self.preconditions.append(node.value)
        elif name == 'ensures':
            self.postconditions.append(node.value)
        else:
            raise AssertionError("Top-level assigns that are not specifications should never happen.")

    def _decorators(self, node: ast.FunctionDef) -> List[str]:
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
        
        return decorators

    def visit_FunctionDef(self, node):
        local = LocalProgramBuilder()
        args, local_vars = local.build(node)
        return_type = None if node.returns is None else self.type_builder.build(node.returns).type
        decs = self._decorators(node)
        function = VyperFunction(node.name, args, local_vars, return_type, self.preconditions, self.postconditions, decs, node)
        self.functions[node.name] = function
        self.preconditions = []
        self.postconditions = []


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

    def __init__(self, type: VyperType, is_public: bool):
        self.type = type
        self.is_public = is_public


class TypeBuilder(ast.NodeVisitor):

    def build(self, node) -> TypeContext:
        return self.visit(node)

    def generic_visit(self, node):
        raise UnsupportedException(node, "Complex types not supported.")

    def visit_Name(self, node: ast.Name) -> TypeContext:
        return TypeContext(TYPES[node.id], False)

    def visit_Call(self, node: ast.Call) -> TypeContext:
        # We allow public and map, constant should already be replaced
        if node.func.id == 'public':
            ctx = self.visit(node.args[0])
            ctx.is_public = True
        elif node.func.id == 'map':
            key_type_ctx = self.visit(node.args[0])
            value_type_ctx = self.visit(node.args[1])
            type = MapType(key_type_ctx.type, value_type_ctx.type)
            ctx = TypeContext(type, False)
        else:
            raise UnsupportedException(node, "Unsupported type.")

        return ctx

