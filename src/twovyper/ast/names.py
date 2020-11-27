"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""


from twovyper.vyper import select_version

# Constants for names in the original AST

# Decorators
PUBLIC = select_version({'^0.2.0': 'external', '>0.1.0-beta.16': 'public'})
PRIVATE = select_version({'^0.2.0': 'internal', '>0.1.0-beta.16': 'private'})
PAYABLE = 'payable'
CONSTANT = select_version({'^0.2.0': 'view', '>0.1.0-beta.16': 'constant'})
NONREENTRANT = 'nonreentrant'
PURE = 'pure'
INTERPRETED_DECORATOR = 'interpreted'

# Modifiers
assert CONSTANT == select_version({'^0.2.0': 'view', '>0.1.0-beta.16': 'constant'})
assert PURE == 'pure'
MODIFYING = select_version({'^0.2.0': 'payable', '>0.1.0-beta.16': 'modifying'})
NONPAYABLE = select_version({'^0.2.0': 'nonpayable'}, default="")

# Types
BOOL = 'bool'
INT128 = 'int128'
UINT256 = 'uint256'
DECIMAL = 'decimal'
WEI_VALUE = 'wei_value'
TIMESTAMP = 'timestamp'
TIMEDELTA = 'timedelta'
ADDRESS = 'address'
BYTE = select_version({'^0.2.0': 'Bytes', '>0.1.0-beta.16': 'bytes'})
BYTES32 = 'bytes32'
STRING = select_version({'^0.2.0': 'String', '>0.1.0-beta.16': 'string'})
# TODO: Mapping declaration syntax changed from v: map(key_t, val_t) to v: HashMap[key_t, val_t]
MAP = select_version({'^0.2.0': 'HashMap', '>0.1.0-beta.16': 'map'})
EVENT = 'event'

# Functions
INIT = '__init__'

# Variables
ADDRESS_BALANCE = 'balance'
ADDRESS_CODESIZE = 'codesize'
ADDRESS_IS_CONTRACT = 'is_contract'
SELF = 'self'
MSG = 'msg'
MSG_SENDER = 'sender'
MSG_VALUE = 'value'
MSG_GAS = 'gas'
BLOCK = 'block'
BLOCK_COINBASE = 'coinbase'
BLOCK_DIFFICULTY = 'difficulty'
BLOCK_NUMBER = 'number'
BLOCK_PREVHASH = 'prevhash'
BLOCK_TIMESTAMP = 'timestamp'
CHAIN = 'chain'
CHAIN_ID = 'id'
TX = 'tx'
TX_ORIGIN = 'origin'
LOG = 'log'
LEMMA = 'lemma'

ENV_VARIABLES = [MSG, BLOCK, CHAIN, TX]

# Constants
EMPTY_BYTES32 = 'EMPTY_BYTES32'
ZERO_ADDRESS = 'ZERO_ADDRESS'
ZERO_WEI = 'ZERO_WEI'
MIN_INT128 = 'MIN_INT128'
MAX_INT128 = 'MAX_INT128'
MAX_UINT256 = 'MAX_UINT256'
MIN_DECIMAL = 'MIN_DECIMAL'
MAX_DECIMAL = 'MAX_DECIMAL'

CONSTANT_VALUES = {
    EMPTY_BYTES32: 'b"' + '\\x00' * 32 + '"',
    ZERO_ADDRESS: '0',
    ZERO_WEI: '0',
    MIN_INT128: f'-{2 ** 127}',
    MAX_INT128: f'{2 ** 127 - 1}',
    MAX_UINT256: f'{2 ** 256 - 1}',
    MIN_DECIMAL: f'-{2 ** 127}.0',
    MAX_DECIMAL: f'{2 ** 127 - 1}.0'
}

# Special
UNITS = 'units'
IMPLEMENTS = 'implements'
INDEXED = 'indexed'
UNREACHABLE = 'UNREACHABLE'

# Ether units
ETHER_UNITS = {
    'wei': 1,
    ('femtoether', 'kwei', 'babbage'): 10 ** 3,
    ('picoether', 'mwei', 'lovelace'): 10 ** 6,
    ('nanoether', 'gwei', 'shannon'): 10 ** 9,
    ('microether', 'szabo'): 10 ** 12,
    ('milliether', 'finney'): 10 ** 15,
    'ether': 10 ** 18,
    ('kether', 'grand'): 10 ** 21
}

# Built-in functions
MIN = 'min'
MAX = 'max'
ADDMOD = 'uint256_addmod'
MULMOD = 'uint256_mulmod'
SQRT = 'sqrt'
FLOOR = 'floor'
CEIL = 'ceil'
SHIFT = 'shift'
BITWISE_NOT = 'bitwise_not'
BITWISE_AND = 'bitwise_and'
BITWISE_OR = 'bitwise_or'
BITWISE_XOR = 'bitwise_xor'

AS_WEI_VALUE = 'as_wei_value'
AS_UNITLESS_NUMBER = 'as_unitless_number'
CONVERT = 'convert'
EXTRACT32 = 'extract32'
EXTRACT32_TYPE = select_version({'^0.2.0': 'output_type', '>0.1.0-beta.16': 'type'})

RANGE = 'range'
LEN = 'len'
CONCAT = 'concat'

KECCAK256 = 'keccak256'
SHA256 = 'sha256'
ECRECOVER = 'ecrecover'
ECADD = 'ecadd'
ECMUL = 'ecmul'

BLOCKHASH = 'blockhash'
METHOD_ID = 'method_id'
METHOD_ID_OUTPUT_TYPE = select_version({'^0.2.0': 'output_type'}, default="")  # TODO: check if its a kwarg
EMPTY = select_version({'^0.2.0': 'empty'}, default="")  # TODO: empty(typename) → Any
# TODO: raise without reasons
# TODO: Various type changes

ASSERT_MODIFIABLE = select_version({'>0.1.0-beta.16': 'assert_modifiable'}, default="")
CLEAR = 'clear'
SELFDESTRUCT = 'selfdestruct'
SEND = 'send'

RAW_CALL = 'raw_call'
RAW_CALL_OUTSIZE = select_version({'^0.2.0': 'max_outsize', '>0.1.0-beta.16': 'outsize'})
RAW_CALL_VALUE = 'value'
RAW_CALL_GAS = 'gas'
RAW_CALL_DELEGATE_CALL = 'delegate_call'
RAW_CALL_IS_STATIC_CALL = select_version({'^0.2.0': 'is_static_call'}, default="")

RAW_LOG = 'raw_log'

CREATE_FORWARDER_TO = 'create_forwarder_to'
CREATE_FORWARDER_TO_VALUE = 'value'

# Verification
INVARIANT = 'invariant'
INTER_CONTRACT_INVARIANTS = 'inter_contract_invariant'
GENERAL_POSTCONDITION = 'always_ensures'
GENERAL_CHECK = 'always_check'
POSTCONDITION = 'ensures'
PRECONDITION = 'requires'
CHECK = 'check'
CALLER_PRIVATE = 'caller_private'
PERFORMS = 'performs'

CONFIG = 'config'
CONFIG_ALLOCATION = 'allocation'
CONFIG_NO_GAS = 'no_gas'
CONFIG_NO_OVERFLOWS = 'no_overflows'
CONFIG_NO_PERFORMS = 'no_performs'
CONFIG_TRUST_CASTS = 'trust_casts'
CONFIG_OPTIONS = [CONFIG_ALLOCATION, CONFIG_NO_GAS, CONFIG_NO_OVERFLOWS, CONFIG_NO_PERFORMS, CONFIG_TRUST_CASTS]

INTERFACE = 'interface'

IMPLIES = 'implies'
FORALL = 'forall'
SUM = 'sum'
TUPLE = 'tuple'
RESULT = 'result'
STORAGE = 'storage'
OLD = 'old'
PUBLIC_OLD = 'public_old'
ISSUED = 'issued'
SENT = 'sent'
RECEIVED = 'received'
ACCESSIBLE = 'accessible'
INDEPENDENT = 'independent'
REORDER_INDEPENDENT = 'reorder_independent'
assert EVENT == 'event'                # EVENT = 'event'
assert SELFDESTRUCT == 'selfdestruct'  # SELFDESTRUCT = 'selfdestruct'
assert IMPLEMENTS == 'implements'      # IMPLEMENTS = 'implements'
LOCKED = 'locked'
REVERT = 'revert'

PREVIOUS = 'previous'
LOOP_ARRAY = 'loop_array'
LOOP_ITERATION = 'loop_iteration'

INTERPRETED = 'interpreted'

CONDITIONAL = 'conditional'

OVERFLOW = 'overflow'
OUT_OF_GAS = 'out_of_gas'
FAILED = 'failed'

CALLER = 'caller'

SUCCESS = 'success'
SUCCESS_IF_NOT = 'if_not'
SUCCESS_OVERFLOW = 'overflow'
SUCCESS_OUT_OF_GAS = 'out_of_gas'
SUCCESS_SENDER_FAILED = 'sender_failed'
SUCCESS_CONDITIONS = [SUCCESS_OVERFLOW, SUCCESS_OUT_OF_GAS, SUCCESS_SENDER_FAILED]

WEI = 'wei'

ALLOCATED = 'allocated'
OFFERED = 'offered'

TRUSTED = 'trusted'
TRUSTED_BY = 'by'

REALLOCATE = 'reallocate'
REALLOCATE_TO = 'to'
REALLOCATE_ACTING_FOR = 'acting_for'

FOREACH = 'foreach'

OFFER = 'offer'
OFFER_TO = 'to'
OFFER_ACTING_FOR = 'acting_for'
OFFER_TIMES = 'times'

REVOKE = 'revoke'
REVOKE_TO = 'to'
REVOKE_ACTING_FOR = 'acting_for'

EXCHANGE = 'exchange'
EXCHANGE_TIMES = 'times'

CREATE = 'create'
CREATE_TO = 'to'
CREATE_ACTING_FOR = 'acting_for'

DESTROY = 'destroy'
DESTROY_ACTING_FOR = 'acting_for'

TRUST = 'trust'
TRUST_ACTING_FOR = 'acting_for'

ALLOCATE_UNTRACKED_WEI = 'allocate_untracked_wei'

CREATOR = 'creator'

GHOST_STATEMENTS = [REALLOCATE, FOREACH, OFFER, REVOKE, EXCHANGE, CREATE, DESTROY, TRUST, ALLOCATE_UNTRACKED_WEI]
QUANTIFIED_GHOST_STATEMENTS = [OFFER, REVOKE, CREATE, DESTROY, TRUST]
SPECIAL_RESOURCES = [WEI, CREATOR]
ALLOCATION_FUNCTIONS = [ALLOCATED, OFFERED, TRUSTED, *GHOST_STATEMENTS]

NOT_ALLOWED_BUT_IN_LOOP_INVARIANTS = [PREVIOUS, LOOP_ARRAY, LOOP_ITERATION]

NOT_ALLOWED_IN_SPEC = [ASSERT_MODIFIABLE, CLEAR, SEND, RAW_CALL, RAW_LOG, CREATE_FORWARDER_TO]
NOT_ALLOWED_IN_INVARIANT = [*NOT_ALLOWED_IN_SPEC, CALLER, OVERFLOW, OUT_OF_GAS, FAILED, ISSUED, BLOCKHASH,
                            INDEPENDENT, REORDER_INDEPENDENT, EVENT, PUBLIC_OLD,  INTERPRETED, CONDITIONAL,
                            *NOT_ALLOWED_BUT_IN_LOOP_INVARIANTS, *GHOST_STATEMENTS]
NOT_ALLOWED_IN_LOOP_INVARIANT = [*NOT_ALLOWED_IN_SPEC, CALLER, ACCESSIBLE, OVERFLOW, OUT_OF_GAS, FAILED,
                                 ACCESSIBLE, INDEPENDENT, REORDER_INDEPENDENT, INTERPRETED, CONDITIONAL,
                                 *GHOST_STATEMENTS]
NOT_ALLOWED_IN_CHECK = [*NOT_ALLOWED_IN_SPEC, CALLER, INDEPENDENT, ACCESSIBLE, PUBLIC_OLD,
                        INTERPRETED, CONDITIONAL, *NOT_ALLOWED_BUT_IN_LOOP_INVARIANTS, *GHOST_STATEMENTS]
NOT_ALLOWED_IN_POSTCONDITION = [*NOT_ALLOWED_IN_SPEC, CALLER, ACCESSIBLE, INTERPRETED, CONDITIONAL,
                                *NOT_ALLOWED_BUT_IN_LOOP_INVARIANTS, *GHOST_STATEMENTS]
NOT_ALLOWED_IN_PRECONDITION = [*NOT_ALLOWED_IN_SPEC, CALLER, ACCESSIBLE, SUCCESS, REVERT, OVERFLOW, OUT_OF_GAS, FAILED,
                               RESULT, ACCESSIBLE, OLD, INDEPENDENT, REORDER_INDEPENDENT,
                               INTERPRETED, CONDITIONAL, *NOT_ALLOWED_BUT_IN_LOOP_INVARIANTS, *GHOST_STATEMENTS]
NOT_ALLOWED_IN_TRANSITIVE_POSTCONDITION = [*NOT_ALLOWED_IN_SPEC, CALLER, OVERFLOW, OUT_OF_GAS, FAILED,
                                           INDEPENDENT, REORDER_INDEPENDENT, EVENT, ACCESSIBLE, PUBLIC_OLD,
                                           INTERPRETED, CONDITIONAL, *NOT_ALLOWED_BUT_IN_LOOP_INVARIANTS,
                                           *GHOST_STATEMENTS]
NOT_ALLOWED_IN_CALLER_PRIVATE = [*NOT_ALLOWED_IN_SPEC, IMPLIES, FORALL, SUM, RESULT, STORAGE, OLD, PUBLIC_OLD, ISSUED,
                                 SENT, RECEIVED, ACCESSIBLE, INDEPENDENT, REORDER_INDEPENDENT, EVENT, SELFDESTRUCT,
                                 IMPLEMENTS, LOCKED, REVERT, OVERFLOW, OUT_OF_GAS, FAILED, SUCCESS,
                                 BLOCKHASH, *ALLOCATION_FUNCTIONS, INTERPRETED, *NOT_ALLOWED_BUT_IN_LOOP_INVARIANTS]
NOT_ALLOWED_IN_GHOST_CODE = [*NOT_ALLOWED_IN_SPEC, CALLER, OVERFLOW, OUT_OF_GAS, FAILED, INDEPENDENT,
                             REORDER_INDEPENDENT, ACCESSIBLE, PUBLIC_OLD, SELFDESTRUCT,
                             CONDITIONAL, *NOT_ALLOWED_BUT_IN_LOOP_INVARIANTS]
NOT_ALLOWED_IN_GHOST_FUNCTION = [*NOT_ALLOWED_IN_SPEC, CALLER, SUCCESS, REVERT, OVERFLOW, OUT_OF_GAS, FAILED, RESULT,
                                 STORAGE, OLD, PUBLIC_OLD, ISSUED, BLOCKHASH, LOCKED, SENT, RECEIVED, ACCESSIBLE,
                                 INDEPENDENT, REORDER_INDEPENDENT, SELFDESTRUCT, INTERPRETED, CONDITIONAL,
                                 *NOT_ALLOWED_BUT_IN_LOOP_INVARIANTS, *GHOST_STATEMENTS]
NOT_ALLOWED_IN_GHOST_STATEMENT = [*NOT_ALLOWED_IN_SPEC, CALLER, SUCCESS, REVERT, OVERFLOW, OUT_OF_GAS, FAILED, RESULT,
                                  ACCESSIBLE, INDEPENDENT, REORDER_INDEPENDENT, PUBLIC_OLD, SELFDESTRUCT,
                                  INTERPRETED, CONDITIONAL, *NOT_ALLOWED_BUT_IN_LOOP_INVARIANTS]
NOT_ALLOWED_IN_LEMMAS = [*NOT_ALLOWED_IN_SPEC, RESULT, STORAGE, OLD, PUBLIC_OLD, ISSUED, SENT, RECEIVED, ACCESSIBLE,
                         INDEPENDENT, REORDER_INDEPENDENT, EVENT, SELFDESTRUCT, IMPLEMENTS, LOCKED, REVERT,
                         INTERPRETED, CONDITIONAL, *NOT_ALLOWED_BUT_IN_LOOP_INVARIANTS, OVERFLOW, OUT_OF_GAS, FAILED,
                         CALLER, SUCCESS, *ALLOCATION_FUNCTIONS]

# Heuristics
WITHDRAW = 'withdraw'
