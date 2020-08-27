"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import os

from twovyper.ast.nodes import VyperProgram, VyperInterface
from twovyper.exceptions import InvalidProgramException
from twovyper.utils import first


def check_symbols(program: VyperProgram):
    _check_unique_ghost_functions(program)
    _check_ghost_implements(program)


def _check_unique_ghost_functions(program: VyperProgram):
    if isinstance(program, VyperInterface):
        for ghost_function in program.own_ghost_functions.values():
            imported_ghost_function = program.imported_ghost_functions.get(ghost_function.name)
            if imported_ghost_function is not None:
                raise InvalidProgramException(ghost_function.node, 'duplicate.ghost',
                                              f'There is already an imported ghost function with the same name '
                                              f'"{ghost_function.name}" from '
                                              f'"{os.path.basename(imported_ghost_function.file)}".')
    else:
        node = first(program.node.stmts) or program.node
        for interface in program.interfaces.values():
            for ghost_function in interface.ghost_functions.values():
                imported_ghost_function = program.ghost_functions.get(ghost_function.name)
                if imported_ghost_function is None:
                    prefix_length = len(os.path.commonprefix([ghost_function.file, program.file]))
                    raise InvalidProgramException(node, 'missing.ghost',
                                                  f'The interface "{interface.name}" '
                                                  f'needs a ghost function "{ghost_function.name}" from '
                                                  f'"{ghost_function.file[prefix_length:]}" but it was not imported '
                                                  f'for this contract.')
                if ghost_function.file != program.ghost_functions[ghost_function.name].file:
                    prefix_length = len(os.path.commonprefix([ghost_function.file, imported_ghost_function.file]))
                    ghost_function_file = ghost_function.file[prefix_length:]
                    imported_ghost_function_file = imported_ghost_function.file[prefix_length:]
                    raise InvalidProgramException(node, 'duplicate.ghost',
                                                  f'There are two versions of the ghost function '
                                                  f'"{ghost_function.name}" one from "{imported_ghost_function_file}" '
                                                  f'the other from "{ghost_function_file}".')


def _check_ghost_implements(program: VyperProgram):
    def check(cond, node):
        if not cond:
            msg = "A ghost function has not been implemented correctly."
            raise InvalidProgramException(node, 'ghost.not.implemented', msg)

    for itype in program.implements:
        interface = program.interfaces[itype.name]
        for ghost in interface.own_ghost_functions.values():
            implementation = program.ghost_function_implementations.get(ghost.name)
            check(implementation, program.node)
            check(implementation.name == ghost.name, implementation.node)
            check(len(implementation.args) == len(ghost.args), implementation.node)
            check(implementation.type == ghost.type, implementation.node)
