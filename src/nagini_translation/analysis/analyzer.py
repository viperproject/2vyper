"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from nagini_translation.ast.nodes import VyperProgram
from nagini_translation.analysis.type_annotator import TypeAnnotator


def analyze(program: VyperProgram):
    """
    Adds type information to all program expressions.
    """
    TypeAnnotator(program).annotate_program()