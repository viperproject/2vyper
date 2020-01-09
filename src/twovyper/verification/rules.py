"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Dict, Tuple


"""Conversion rules from Silver level errors to 2vyper errors."""
Rules = Dict[Tuple[str, str], Tuple[str, str]]


INVARIANT_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('invariant.violated', 'assertion.false'),
    ('assert.failed', 'division.by.zero'):
        ('invariant.not.wellformed', 'division.by.zero'),
    ('assert.failed', 'seq.index.length'):
        ('invariant.not.wellformed', 'seq.index.length'),
    ('assert.failed', 'seq.index.negative'):
        ('invariant.not.wellformed', 'seq.index.negative')
}

POSTCONDITION_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('postcondition.violated', 'assertion.false'),
    ('assert.failed', 'division.by.zero'):
        ('not.wellformed', 'division.by.zero'),
    ('assert.failed', 'seq.index.length'):
        ('not.wellformed', 'seq.index.length'),
    ('assert.failed', 'seq.index.negative'):
        ('not.wellformed', 'seq.index.negative')
}

INTERFACE_POSTCONDITION_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('postcondition.not.implemented', 'assertion.false')
}

CHECK_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('check.violated', 'assertion.false'),
    ('assert.failed', 'division.by.zero'):
        ('not.wellformed', 'division.by.zero'),
    ('assert.failed', 'seq.index.length'):
        ('not.wellformed', 'seq.index.length'),
    ('assert.failed', 'seq.index.negative'):
        ('not.wellformed', 'seq.index.negative')
}

CALL_INVARIANT_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('call.invariant', 'assertion.false')
}

CALL_CHECK_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('call.check', 'assertion.false')
}

CALL_LEAK_CHECK_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('call.leakcheck', 'allocation.leaked')
}

INHALE_INVARIANT_FAIL = {
    ('inhale.failed', 'division.by.zero'):
        ('invariant.not.wellformed', 'division.by.zero'),
    ('inhale.failed', 'seq.index.length'):
        ('invariant.not.wellformed', 'seq.index.length'),
    ('inhale.failed', 'seq.index.negative'):
        ('invariant.not.wellformed', 'seq.index.negative')
}

INHALE_POSTCONDITION_FAIL = {
    ('inhale.failed', 'division.by.zero'):
        ('postcondition.not.wellformed', 'division.by.zero'),
    ('inhale.failed', 'seq.index.length'):
        ('postcondition.not.wellformed', 'seq.index.length'),
    ('inhale.failed', 'seq.index.negative'):
        ('postcondition.not.wellformed', 'seq.index.negative')
}

INHALE_INTERFACE_FAIL = {
    ('inhale.failed', 'division.by.zero'):
        ('interface.postcondition.not.wellformed', 'division.by.zero'),
    ('inhale.failed', 'seq.index.length'):
        ('interface.postcondition.not.wellformed', 'seq.index.length'),
    ('inhale.failed', 'seq.index.negative'):
        ('interface.postcondition.not.wellformed', 'seq.index.negative')
}

INVARIANT_TRANSITIVITY_VIOLATED = {
    ('assert.failed', 'assertion.false'):
        ('invariant.not.wellformed', 'transitivity.violated')
}

POSTCONDITION_TRANSITIVITY_VIOLATED = {
    ('assert.failed', 'assertion.false'):
        ('postcondition.not.wellformed', 'transitivity.violated')
}

POSTCONDITION_CONSTANT_BALANCE = {
    ('assert.failed', 'assertion.false'):
        ('postcondition.not.wellformed', 'constant.balance')
}

PRECONDITION_IMPLEMENTS_INTERFACE = {
    ('application.precondition', 'assertion.false'):
        ('application.precondition', 'not.implements.interface')
}

REALLOCATE_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('reallocate.failed', 'insufficient.funds')
}

EXCHANGE_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('exchange.failed', 'insufficient.funds')
}

ALLOCATION_LEAK_CHECK_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('leakcheck.failed', 'allocation.leaked')
}
