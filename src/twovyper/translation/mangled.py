"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from twovyper.ast import names


# Constants for names in translated AST

INIT = names.INIT

SELF = names.SELF
CONTRACTS = '$contracts'

MSG = names.MSG
BLOCK = names.BLOCK
TX = names.TX

SENT_FIELD = '$sent'
RECEIVED_FIELD = '$received'
SELFDESTRUCT_FIELD = '$selfdestruct'

RESULT_VAR = '$res'
SUCCESS_VAR = '$succ'

OVERFLOW = '$overflow'
OUT_OF_GAS = '$out_of_gas'
FAILED = '$failed'

FIRST_PUBLIC_STATE = '$first_public_state'

END_LABEL = 'end'
RETURN_LABEL = 'return'
REVERT_LABEL = 'revert'

BLOCKCHAIN_DOMAIN = '$Blockchain'
BLOCKCHAIN_BLOCKHASH = '$blockhash'
BLOCKCHAIN_METHOD_ID = '$method_id'
BLOCKCHAIN_KECCAK256 = '$keccak256'
BLOCKCHAIN_SHA256 = '$sha256'
BLOCKCHAIN_ECRECOVER = '$ecrecover'
BLOCKCHAIN_ECADD = '$ecadd'
BLOCKCHAIN_ECMUL = '$ecmul'

CONTRACT_DOMAIN = '$Contract'
SELF_ADDRESS = '$self_address'
IMPLEMENTS = '$implements'

MATH_DOMAIN = '$Math'
MATH_SIGN = '$sign'
MATH_DIV = '$div'
MATH_MOD = '$mod'
MATH_POW = '$pow'
MATH_SQRT = '$sqrt'
MATH_FLOOR = '$floor'
MATH_CEIL = '$ceil'
MATH_SHIFT = '$shift'
MATH_BITWISE_NOT = '$bitwise_not'
MATH_BITWISE_AND = '$bitwise_and'
MATH_BITWISE_OR = '$bitwise_or'
MATH_BITWISE_XOR = '$bitwise_xor'

ARRAY_DOMAIN = '$Array'
ARRAY_INT_DOMAIN = '$ArrayInt'
ARRAY_ELEMENT_VAR = '$E'
ARRAY_INIT = '$array_init'

MAP_DOMAIN = '$Map'
MAP_INT_DOMAIN = '$MapInt'
MAP_KEY_VAR = '$K'
MAP_VALUE_VAR = '$V'

MAP_INIT = '$map_init'
MAP_EQ = '$map_eq'
MAP_GET = '$map_get'
MAP_SET = '$map_set'
MAP_SUM = '$map_sum'

STRUCT_DOMAIN = '$Struct'
STRUCT_OPS_DOMAIN = '$StructOps'
STRUCT_OPS_VALUE_VAR = '$T'

STRUCT_LOC = '$struct_loc'
STRUCT_GET = '$struct_get'
STRUCT_SET = '$struct_set'

STRUCT_INIT_DOMAIN = '$StructInit'

RANGE_DOMAIN = '$Range'
RANGE_RANGE = '$range'

CONVERT_DOMAIN = '$Convert'
CONVERT_BYTES32_TO_SIGNED_INT = '$bytes32_to_signed_int'
CONVERT_BYTES32_TO_UNSIGNED_INT = '$bytes32_to_unsigned_int'
CONVERT_SIGNED_INT_TO_BYTES32 = '$signed_int_to_bytes32'
CONVERT_UNSIGNED_INT_TO_BYTES32 = '$unsigned_int_to_bytes32'
CONVERT_PAD32 = '$pad32'

IMPLEMENTS_DOMAIN = '$Implements'

TRANSITIVITY_CHECK = '$transitivity_check'
FORCED_ETHER_CHECK = '$forced_ether_check'


def method_name(vyper_name: str) -> str:
    return f'f${vyper_name}'


def struct_name(vyper_struct_name: str) -> str:
    return f's${vyper_struct_name}'


def struct_init_name(vyper_struct_name: str) -> str:
    return f'{struct_name(vyper_struct_name)}$init'


def struct_eq_name(vyper_struct_name: str) -> str:
    return f'{struct_name(vyper_struct_name)}$eq'


def interface_name(vyper_interface_name: str) -> str:
    return f'i${vyper_interface_name}'


def interface_function_name(vyper_iname: str, vyper_fname: str) -> str:
    return f'{interface_name(vyper_iname)}${vyper_fname}'


def ghost_function_name(vyper_name: str) -> str:
    return f'g${vyper_name}'


def axiom_name(viper_name: str) -> str:
    return f'{viper_name}$ax'


def ghost_axiom_name(vyper_name: str, idx: int):
    return axiom_name(f'{ghost_function_name(vyper_name)}${idx}')


def event_name(vyper_name: str) -> str:
    return f'e${vyper_name}'


def accessible_name(vyper_name: str) -> str:
    return f'$accessible${vyper_name}'


def lock_name(vyper_name: str) -> str:
    return f'r${vyper_name}'


def local_var_name(inline_prefix: str, vyper_name: str) -> str:
    if vyper_name in {names.SELF, names.MSG, names.BLOCK}:
        prefix = ''
    else:
        prefix = 'l$'
    return f'{prefix}{inline_prefix}{vyper_name}'


def quantifier_var_name(vyper_name: str) -> str:
    return f'q${vyper_name}'


def model_var_name(*components: str) -> str:
    return f'm${"$".join(components)}'
