"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import re

from twovyper.ast.names import RESOURCE_PREFIX, DERIVED_RESOURCE_PREFIX


def preprocess(program: str) -> str:
    # Make specifications valid python statements. We use assignments instead of variable
    # declarations because we could have contract variables called 'ensures'.
    # Padding with spaces is used to keep the column numbers correct in the preprocessed program.

    def padding(old_length: int, match_length: int) -> str:
        return (match_length - old_length) * ' '

    def replacement(start: str, end: str):
        old_length = len(start) + len(end)
        return lambda m: f'{start}{padding(old_length, len(m.group(0)))}{end}'

    def replace(regex, repl):
        nonlocal program
        program = re.sub(regex, repl, program, flags=re.MULTILINE)

    replace(r'#@\s*config\s*:', replacement('config', '='))
    replace(r'#@\s*interface', replacement('internal_interface', '=True'))
    replace(r'#@\s*ghost\s*:', replacement('with(g)', ':'))
    replace(r'#@\s*resource\s*:\s*', replacement('def ', RESOURCE_PREFIX))
    replace(r'#@\s*derived\s*resource\s*:\s*', replacement('def ', DERIVED_RESOURCE_PREFIX))
    replace(r'#@\s*ensures\s*:', replacement('ensures', '='))
    replace(r'#@\s*requires\s*:', replacement('requires', '='))
    replace(r'#@\s*check\s*:', replacement('check', '='))
    replace(r'#@\s*performs\s*:', replacement('performs', '='))
    replace(r'#@\s*invariant\s*:', replacement('invariant', '='))
    replace(r'#@\s*inter\s*contract\s*invariant\s*:', replacement('inter_contract_invariant', '='))
    replace(r'#@\s*always\s*ensures\s*:', replacement('always_ensures', '='))
    replace(r'#@\s*always\s*check\s*:', replacement('always_check', '='))
    replace(r'#@\s*caller\s*private\s*:', replacement('caller_private', '='))
    replace(r'#@\s*preserves\s*:', replacement('if False', ':'))
    replace(r'#@\s*pure', replacement('@pure', ''))
    replace(r'#@\s*interpreted', replacement('@interpreted', ''))
    replace(r'#@\s*lemma_def', replacement('def', ''))
    replace(r'#@\s*lemma_assert', replacement('assert', ''))
    return program
