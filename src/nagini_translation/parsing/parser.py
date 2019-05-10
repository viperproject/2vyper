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
from nagini_translation.ast.types import TypeBuilder, TypeContext

from nagini_translation.ast import names
from nagini_translation.ast import types

from nagini_translation.ast.nodes import VyperProgram, VyperFunction, VyperVar
from nagini_translation.ast.types import VyperType, FunctionType, MapType, ArrayType

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
        if name == names.INVARIANT:
            # No preconditions and posconditions allowed before invariants
            self._check_no_prepostconditions()

            self.invariants.append(node.value)
        elif name == names.PRECONDITION:
            self.preconditions.append(node.value)
        elif name == names.POSTCONDITION:
            self.postconditions.append(node.value)
        else:
            raise AssertionError("Top-level assigns that are not specifications should never happen.")

    def _decorators(self, node: ast.FunctionDef) -> List[str]:
        return [dec.id for dec in node.decorator_list if isinstance(dec, ast.Name)]

    def visit_FunctionDef(self, node):
        local = LocalProgramBuilder()
        args, local_vars = local.build(node)
        arg_types = [arg.type for arg in args.values()]
        return_type = None if node.returns is None else self.type_builder.build(node.returns).type
        type = FunctionType(arg_types, return_type)
        decs = self._decorators(node)
        function = VyperFunction(node.name, args, local_vars, type, self.preconditions, self.postconditions, decs, node)
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
        variable_type = types.VYPER_INT128
        var = VyperVar(variable_name, variable_type, node)
        self.local_vars[variable_name] = var
        self.generic_visit(node)
