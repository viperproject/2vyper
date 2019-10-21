"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import re


def preprocess(program: str) -> str:
    # Change structs to classes
    program = re.sub(r'(?<=^)struct(?=\s.*:\s*$)', r'class ', program, flags=re.MULTILINE)
    # Change contracts to classes
    program = re.sub(r'(?<=^)contract(?=\s.*:\s*$)', r'class   ', program, flags=re.MULTILINE)

    # Make specifications valid python statements. We use assignments instead of variable
    # declarations because we could have contract variables called 'ensures'.
    # The spaces are used to keep the column numbers correct in the preprocessed program.
    program = program.replace('#@ config:', 'config   =')
    program = program.replace('#@ pure', 'pure = True')
    program = program.replace('#@ ensures:', 'ensures   =')
    program = program.replace('#@ check:', 'check   =')
    program = program.replace('#@ invariant:', 'invariant   =')
    program = program.replace('#@ always ensures:', 'always_ensures   =')
    program = program.replace('#@ always check:', 'always_check   =')
    program = program.replace('#@ preserves:', 'if False:     ')
    program = program.replace('#@', '  ')
    return program
