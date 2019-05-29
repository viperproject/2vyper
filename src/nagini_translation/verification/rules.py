"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Dict, Tuple


"""Conversion rules from Silver level errors to Nagini errors."""
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

CALL_INVARIANT_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('call.invariant', 'assertion.false')
}

INHALE_INVARIANT_FAIL = {
    ('inhale.failed', 'division.by.zero'):
        ('invariant.not.wellformed', 'division.by.zero'),
    ('inhale.failed', 'seq.index.length'):
        ('invariant.not.wellformed', 'seq.index.length'),
    ('inhale.failed', 'seq.index.negative'):
        ('invariant.not.wellformed', 'seq.index.negative')
}

TRANSITIVITY_VIOLATED = {
    ('assert.failed', 'assertion.false'):
        ('invariant.not.wellformed', 'transitivity.violated')
}
