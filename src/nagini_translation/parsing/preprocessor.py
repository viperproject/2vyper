"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from nagini_translation.errors.translation import InvalidProgramException


def preprocess(program: str) -> str:
    # Make preconditions valid python statements. We use assignments instead of variable
    # declarations because we could have contract variables called 'requires'.
    # The spaces are used to keep the column numbers correct in the preprocessed program.
    program = program.replace('#@ requires:', 'requires   =')
    program = program.replace('#@ ensures:', 'ensures   =')
    program = program.replace('#@ invariant:', 'invariant   =')
    program = program.replace('#@ always ensures:', 'always_ensures   =')

    if '#@' in program:
        raise InvalidProgramException(None, "Invalid specification: #@ not allowed here.")

    return program
