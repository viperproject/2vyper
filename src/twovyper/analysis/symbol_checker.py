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


def _check_unique_ghost_functions(program: VyperProgram):
    if not isinstance(program, VyperInterface):
        ghosts = sum(len(interface.ghost_functions) for interface in program.interfaces.values())
        if ghosts != len(program.ghost_functions):
            raise InvalidProgramException(program.node, 'duplicate.ghost')
