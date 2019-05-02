"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""


# Decorators
PUBLIC = 'public'
PRIVATE = 'private'

# Types
MAP = 'map'

# Variables
SELF = 'self'
MSG = 'msg'

# Constants
ZERO_ADDRESS = 'ZERO_ADDRESS'

CONSTANT_VALUES = {
    ZERO_ADDRESS: 0
}

# Built-in functions
RANGE = 'range'
MIN = 'min'
MAX = 'max'

# Verification
INVARIANT = 'invariant'
PRECONDITION = 'requires'
POSTCONDITION = 'ensures'

IMPLIES = 'implies'
SUCCESS = 'success'
RESULT = 'result'
OLD = 'old'