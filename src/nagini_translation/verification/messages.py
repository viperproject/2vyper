"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

# Conversion of errors to human readable messages.

from nagini_translation.utils import pprint


ERRORS = {
    'assignment.failed':
        lambda i: "Assignment might fail.",
    'call.failed':
        lambda i: "Method call might fail.",
    'not.wellformed':
        lambda i: f"Function {i.function} might not be well-formed.",
    'call.invariant':
        lambda i: f"An invariant might not hold before the call {pprint(i.node)}.",
    'call.check':
        lambda i: f"A check might not hold before the call {pprint(i.node)}.",
    'call.precondition':
        lambda i: f"The precondition of function {pprint(i.node)} might not hold.",
    'application.precondition':
        lambda i: f"The precondition of function {pprint(i.node)} might not hold.",
    'exhale.failed':
        lambda i: "Exhale might fail.",
    'inhale.failed':
        lambda i: "Inhale might fail.",
    'if.failed':
        lambda i: "Conditional statement might fail.",
    'while.failed':
        lambda i: "While statement might fail.",
    'assert.failed':
        lambda i: "Assert might fail.",
    'postcondition.violated':
        lambda i: f"Postcondition of {i.function} might not hold.",
    'invariant.violated':
        lambda i: f"Invariant not preserved by {i.function}.",
    'check.violated':
        lambda i: f"A check might not hold after the body of {i.function}.",
    'invariant.not.wellformed':
        lambda i: f"Invariant {pprint(i.node)} might not be well-formed.",
    'fold.failed':
        lambda i: "Fold might fail.",
    'unfold.failed':
        lambda i: "Unfold might fail.",
    'invariant.not.preserved':
        lambda i: "Loop invariant might not be preserved.",
    'invariant.not.established':
        lambda i: "Loop invariant might not hold on entry.",
    'function.not.wellformed':
        lambda i: "Function might not be well-formed.",
    'predicate.not.wellformed':
        lambda i: "Predicate might not be well-formed."
}

REASONS = {
    'assertion.false':
        lambda i: f"Assertion {pprint(i.node)} might not hold.",
    'transitivity.violated':
        lambda i: "Invariant might not be transitive.",
    'division.by.zero':
        lambda i: f"Divisor {pprint(i.node)} might be zero.",
    'seq.index.length':
        lambda i: f"Index {pprint(i.node)} might exceed array length.",
    'seq.index.negative':
        lambda i: f"Index {pprint(i.node)} might be negative.",
    'receiver.not.injective':
        lambda i: f"Receiver of {pprint(i.node)} might not be injective.",
    'receiver.null':
        lambda i: f"Receiver of {pprint(i.node)} might be null.",
    'negative.permission':
        lambda i: f"Fraction {pprint(i.node)} might be negative.",
    'insufficient.permission':
        lambda i: f"There might be insufficient permission to access {pprint(i.node)}."
}

VAGUE_REASONS = {
    'assertion.false': "",
    'receiver.null': "Receiver might be null.",
    'division.by.zero': "Divisor might be zero.",
    'negative.permission': "Fraction might be negative.",
    'insufficient.permission': "There might be insufficient permission."
}
