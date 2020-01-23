"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from twovyper.ast.nodes import VyperProgram, VyperInterface

from twovyper.exceptions import InvalidProgramException


def check_symbols(program: VyperProgram):
    _check_unique_ghost_functions(program)
    _check_ghost_implements(program)


def _check_unique_ghost_functions(program: VyperProgram):
    if not isinstance(program, VyperInterface):
        ghosts = sum(len(interface.ghost_functions) for interface in program.interfaces.values())
        if ghosts != len(program.ghost_functions):
            raise InvalidProgramException(program.node, 'duplicate.ghost')


def _check_ghost_implements(program: VyperProgram):
    def check(cond, node):
        if not cond:
            msg = "A ghost function has not been implemented correctly."
            raise InvalidProgramException(node, 'ghost.not.implemented', msg)

    for itype in program.implements:
        interface = program.interfaces[itype.name]
        for ghost in interface.ghost_functions.values():
            implementation = program.ghost_function_implementations.get(ghost.name)
            check(implementation, program.node)
            check(implementation.name == ghost.name, implementation.node)
            check(len(implementation.args) == len(ghost.args), implementation.node)
            check(implementation.type == ghost.type, implementation.node)
