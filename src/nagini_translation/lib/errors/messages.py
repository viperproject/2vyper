"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from nagini_translation.lib.util import pprint

"""Conversion of errors to human readable messages."""

ERRORS = {
    'assignment.failed':
        lambda i: 'Assignment might fail.',
    'call.failed':
        lambda i: 'Method call might fail.',
    'not.wellformed':
        lambda i: 'Contract might not be well-formed.',
    'call.invariant':
        lambda i: f"An invariant might not hold before the call {pprint(i.node)}.",
    'call.precondition':
        lambda i: f"The precondition of function {pprint(i.node)} might not hold.",
    'application.precondition':
        lambda i: (f"The precondition of function {i.function} might not hold."
                   if isinstance(i.node, (ast.Call, ast.FunctionDef)) else
                   'The precondition of {} might not hold.'.format(pprint(i.node))),
    'exhale.failed':
        lambda i: 'Exhale might fail.',
    'inhale.failed':
        lambda i: 'Inhale might fail.',
    'if.failed':
        lambda i: 'Conditional statement might fail.',
    'while.failed':
        lambda i: 'While statement might fail.',
    'assert.failed':
        lambda i: 'Assert might fail.',
    'postcondition.violated':
        lambda i: f"Postcondition of {i.function} might not hold.",
    'invariant.violated':
        lambda i: f"Invariant not preserved by {i.function}.",
    'fold.failed':
        lambda i: 'Fold might fail.',
    'unfold.failed':
        lambda i: 'Unfold might fail.',
    'invariant.not.preserved':
        lambda i: 'Loop invariant might not be preserved.',
    'invariant.not.established':
        lambda i: 'Loop invariant might not hold on entry.',
    'function.not.wellformed':
        lambda i: ('Function {} might not be '
                   'well-formed.'),
    'predicate.not.wellformed':
        lambda i: ('Predicate {} might not be '
                   'well-formed.')
}

REASONS = {
    'assertion.false':
        lambda i: 'Assertion {} might not hold.'.format(pprint(i.node)),
    'receiver.null':
        lambda i: 'Receiver of {} might be null.'.format(pprint(i.node)),
    'division.by.zero':
        lambda i: 'Divisor {} might be zero.'.format(pprint(i.node)),
    'seq.index.length':
        lambda i: f"Index {pprint(i.node)} might exceed sequence length.",
    'negative.permission':
        lambda i: 'Fraction {} might be negative.'.format(pprint(i.node)),
    'insufficient.permission':
        lambda i: ('There might be insufficient permission to '
                   'access {}.').format(pprint(i.node))
}

VAGUE_REASONS = {
    'assertion.false': '',
    'receiver.null': 'Receiver might be null.',
    'division.by.zero': 'Divisor might be zero.',
    'negative.permission': 'Fraction might be negative.',
    'insufficient.permission': 'There might be insufficient permission.'
}
