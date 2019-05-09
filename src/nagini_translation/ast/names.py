"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

# Constants for names in the original AST

# Decorators
PUBLIC = 'public'
PRIVATE = 'private'
PAYABLE = 'payable'

# Types
BOOL = 'bool'
WEI_VALUE = 'wei_value'
INT128 = 'int128'
UINT256 = 'uint256'
ADDRESS = 'address'
MAP = 'map'

# Functions
INIT = '__init__'

# Variables
SELF = 'self'
SELF_BALANCE = 'balance'
MSG = 'msg'
MSG_SENDER = 'sender'

# Constants
ZERO_ADDRESS = 'ZERO_ADDRESS'

CONSTANT_VALUES = {
    ZERO_ADDRESS: 0
}

# Built-in functions
RANGE = 'range'
MIN = 'min'
MAX = 'max'
CLEAR = 'clear'

# Verification
INVARIANT = 'invariant'
FORALL = 'forall'
PRECONDITION = 'requires'
POSTCONDITION = 'ensures'

IMPLIES = 'implies'
SUCCESS = 'success'
RESULT = 'result'
OLD = 'old'
SUM = 'sum'