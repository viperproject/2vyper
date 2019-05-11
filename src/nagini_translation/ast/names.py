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
MSG_VALUE = 'value'

# Constants
ZERO_ADDRESS = 'ZERO_ADDRESS'

CONSTANT_VALUES = {
    ZERO_ADDRESS: 0
}

# Ether units
ETHER_UNITS = {
    'wei': 1,
    'kwei': 1_000,
    'babbage': 1_000,
    'mwei': 1_000_000,
    'lovelace': 1_000_000,
    'gwei': 1_000_000_000,
    'shannon': 1_000_000_000,
    'microether': 1_000_000_000_000,
    'szabo': 1_000_000_000_000,
    'milliether': 1_000_000_000_000_000,
    'finney': 1_000_000_000_000_000,
    'ether': 1_000_000_000_000_000_000
}

# Built-in functions
RANGE = 'range'
MIN = 'min'
MAX = 'max'
CLEAR = 'clear'
SEND = 'send'
AS_WEI_VALUE = 'as_wei_value'
AS_UNITLESS_NUMBER = 'as_unitless_number'

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