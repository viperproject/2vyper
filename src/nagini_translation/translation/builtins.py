"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from nagini_translation.ast import names
from nagini_translation.ast.types import FunctionType, StructType
from nagini_translation.ast.nodes import VyperFunction

from nagini_translation.viper.ast import ViperAST


# Constants for names in translated AST


INIT = names.INIT
SELF = names.SELF
OLD_SELF = f'$old_{names.SELF}'
PRE_SELF = f'$pre_{names.SELF}'
ISSUED_SELF = f'$issued_{names.SELF}'
SELF_BALANCE = 's$balance'

MSG = names.MSG
MSG_SENDER = f's${names.MSG_SENDER}'
MSG_VALUE = f's${names.MSG_VALUE}'

BLOCK = names.BLOCK
BLOCK_TIMESTAMP = f's${names.BLOCK_TIMESTAMP}'

SENT_FIELD = '$sent'
RECEIVED_FIELD = '$received'

RESULT_VAR = '$res'
SUCCESS_VAR = '$succ'

OUT_OF_GAS = '$out_of_gas'
MSG_SENDER_CALL_FAIL = '$msg_sender_call_fail'

END_LABEL = 'end'
RETURN_LABEL = 'return'
REVERT_LABEL = 'revert'

CONTRACT_DOMAIN = '$Contract'
SELF_ADDRESS = '$self_address'

MATH_DOMAIN = '$Math'
MATH_POW = '$pow'

ARRAY_DOMAIN = '$Array'
ARRAY_INT_DOMAIN = '$ArrayInt'
ARRAY_ELEMENT_VAR = '$E'

ARRAY_INIT = '$array_init'
ARRAY_KECCAK256 = '$array_keccak256'
ARRAY_SHA256 = '$array_sha256'

MAP_DOMAIN = '$Map'
MAP_INT_DOMAIN = '$MapInt'
MAP_KEY_VAR = '$K'
MAP_VALUE_VAR = '$V'

MAP_INIT = '$map_init'
MAP_GET = '$map_get'
MAP_SET = '$map_set'
MAP_SUM = '$map_sum'

TRANSITIVITY_CHECK = '$transitivity_check'


def method_name(vyper_name: str) -> str:
    return f'f${vyper_name}'


def struct_name(vyper_name: str) -> str:
    return f'd${vyper_name}'


def struct_member_name(vyper_struct_name: str, vyper_member_name: str) -> str:
    return f'd${vyper_struct_name}${vyper_member_name}'


def struct_member_getter_name(vyper_struct_name: str, vyper_member_name: str) -> str:
    return f'd${vyper_struct_name}$get_{vyper_member_name}'


def struct_member_setter_name(vyper_struct_name: str, vyper_member_name: str) -> str:
    return f'd${vyper_struct_name}$set_{vyper_member_name}'


def struct_field_name(vyper_struct_name: str) -> str:
    return f'd${vyper_struct_name}$field'


def struct_init_name(vyper_struct_name: str) -> str:
    return f'd${vyper_struct_name}$init'


def axiom_name(viper_name: str) -> str:
    return f'{viper_name}_ax'


def event_name(vyper_name: str) -> str:
    return f'e${vyper_name}'


def field_name(vyper_name: str) -> str:
    if vyper_name in {SENT_FIELD, RECEIVED_FIELD}:
        return vyper_name
    else:
        return f's${vyper_name}'


def local_var_name(vyper_name: str) -> str:
    if vyper_name in {SELF, MSG, BLOCK}:
        return vyper_name
    else:
        return f'l${vyper_name}'


def quantifier_var_name(vyper_name: str) -> str:
    return f'q${vyper_name}'


def read_perm(viper_ast: ViperAST, pos=None, info=None):
    one = viper_ast.IntLit(1, pos, info)
    two = viper_ast.IntLit(2, pos, info)
    return viper_ast.FractionalPerm(one, two, pos, info)


def init_function() -> ast.FunctionDef:
    node = ast.FunctionDef(INIT, [], [], [], None)
    type = FunctionType([], None)
    return VyperFunction(INIT, {}, {}, type, [], [], [], [names.PUBLIC], node)


def self_var(viper_ast: ViperAST, self_type: StructType, pos=None, info=None):
    type = struct_type(viper_ast, self_type)
    return viper_ast.LocalVarDecl(SELF, type, pos, info)


def old_self_var(viper_ast: ViperAST, self_type: StructType, pos=None, info=None):
    type = struct_type(viper_ast, self_type)
    return viper_ast.LocalVarDecl(OLD_SELF, type, pos, info)


def pre_self_var(viper_ast: ViperAST, self_type: StructType, pos=None, info=None):
    type = struct_type(viper_ast, self_type)
    return viper_ast.LocalVarDecl(PRE_SELF, type, pos, info)


def issued_self_var(viper_ast: ViperAST, self_type: StructType, pos=None, info=None):
    type = struct_type(viper_ast, self_type)
    return viper_ast.LocalVarDecl(ISSUED_SELF, type, pos, info)


def msg_var(viper_ast: ViperAST, pos=None, info=None):
    return viper_ast.LocalVarDecl(MSG, viper_ast.Ref, pos, info)


def msg_sender_field(viper_ast: ViperAST, pos=None, info=None):
    return viper_ast.Field(MSG_SENDER, viper_ast.Int, pos, info)


def msg_sender_field_acc(viper_ast: ViperAST, pos=None, info=None):
    msg = msg_var(viper_ast, pos, info).localVar()
    field = msg_sender_field(viper_ast, pos, info)
    return viper_ast.FieldAccess(msg, field, pos, info)


def msg_value_field(viper_ast: ViperAST, pos=None, info=None):
    return viper_ast.Field(MSG_VALUE, viper_ast.Int, pos, info)


def msg_value_field_acc(viper_ast: ViperAST, pos=None, info=None):
    msg = msg_var(viper_ast, pos, info).localVar()
    field = msg_value_field(viper_ast, pos, info)
    return viper_ast.FieldAccess(msg, field, pos, info)


def block_var(viper_ast: ViperAST, pos=None, info=None):
    return viper_ast.LocalVarDecl(BLOCK, viper_ast.Ref, pos, info)


def block_timestamp_field(viper_ast: ViperAST, pos=None, info=None):
    return viper_ast.Field(BLOCK_TIMESTAMP, viper_ast.Int, pos, info)


def ret_var(viper_ast: ViperAST, ret_type, pos=None, info=None):
    return viper_ast.LocalVarDecl(RESULT_VAR, ret_type, pos, info)


def success_var(viper_ast: ViperAST, pos=None, info=None):
    return viper_ast.LocalVarDecl(SUCCESS_VAR, viper_ast.Bool, pos, info)


def out_of_gas_var(viper_ast: ViperAST, pos=None, info=None):
    return viper_ast.LocalVarDecl(OUT_OF_GAS, viper_ast.Bool, pos, info)


def msg_sender_call_fail_var(viper_ast: ViperAST, pos=None, info=None):
    return viper_ast.LocalVarDecl(MSG_SENDER_CALL_FAIL, viper_ast.Bool, pos, info)


def self_address(viper_ast: ViperAST, pos=None, info=None):
    return viper_ast.DomainFuncApp(SELF_ADDRESS, [], viper_ast.Int, pos, info, CONTRACT_DOMAIN)


def pow(viper_ast: ViperAST, base, exp, pos=None, info=None):
    return viper_ast.DomainFuncApp(MATH_POW, [base, exp], viper_ast.Int, pos, info, MATH_DOMAIN)


def array_type(viper_ast: ViperAST, element_type):
    return viper_ast.SeqType(element_type)


def array_init(viper_ast: ViperAST, arg, size: int, element_type, pos=None, info=None):
    arr_type = array_type(viper_ast, element_type)
    type_vars = {viper_ast.TypeVar(ARRAY_ELEMENT_VAR): element_type}
    size = viper_ast.IntLit(size, pos, info)
    return viper_ast.DomainFuncApp(ARRAY_INIT, [arg, size], arr_type, pos, info, ARRAY_DOMAIN, type_vars)


def array_keccak256(viper_ast: ViperAST, arg, pos=None, info=None):
    int_array_type = viper_ast.SeqType(viper_ast.Int)
    return viper_ast.DomainFuncApp(ARRAY_KECCAK256, [arg], int_array_type, pos, info, ARRAY_INT_DOMAIN)


def array_sha256(viper_ast: ViperAST, arg, pos=None, info=None):
    int_array_type = viper_ast.SeqType(viper_ast.Int)
    return viper_ast.DomainFuncApp(ARRAY_SHA256, [arg], int_array_type, pos, info, ARRAY_INT_DOMAIN)


def array_length(viper_ast: ViperAST, ref, pos=None, info=None):
    return viper_ast.SeqLength(ref, pos, info)


def array_get(viper_ast: ViperAST, ref, idx, element_type, pos=None, info=None):
    return viper_ast.SeqIndex(ref, idx, pos, info)


def array_set(viper_ast: ViperAST, ref, idx, value, element_type, pos=None, info=None):
    return viper_ast.SeqUpdate(ref, idx, value, pos, info)


def array_contains(viper_ast: ViperAST, value, ref, pos=None, info=None):
    return viper_ast.SeqContains(value, ref, pos, info)


def array_not_contains(viper_ast: ViperAST, value, ref, pos=None, info=None):
    return viper_ast.Not(array_contains(viper_ast, value, ref, pos, info), pos, info)


def _map_type_var_map(viper_ast: ViperAST, key_type, value_type):
    key = viper_ast.TypeVar(MAP_KEY_VAR)
    value = viper_ast.TypeVar(MAP_VALUE_VAR)
    return {key: key_type, value: value_type}


def map_type(viper_ast: ViperAST, key_type, value_type):
    type_vars = _map_type_var_map(viper_ast, key_type, value_type)
    return viper_ast.DomainType(MAP_DOMAIN, type_vars, type_vars.keys())


def map_init(viper_ast: ViperAST, arg, key_type, value_type, pos=None, info=None):
    mp_type = map_type(viper_ast, key_type, value_type)
    type_vars = _map_type_var_map(viper_ast, key_type, value_type)
    return viper_ast.DomainFuncApp(MAP_INIT, [arg], mp_type, pos, info, MAP_DOMAIN, type_vars)


def map_get(viper_ast: ViperAST, ref, idx, key_type, value_type, pos=None, info=None):
    type_vars = _map_type_var_map(viper_ast, key_type, value_type)
    return viper_ast.DomainFuncApp(MAP_GET, [ref, idx], value_type, pos, info, MAP_DOMAIN, type_vars)


def map_set(viper_ast: ViperAST, ref, idx, value, key_type, value_type, pos=None, info=None):
    type_vars = _map_type_var_map(viper_ast, key_type, value_type)
    type = map_type(viper_ast, key_type, value_type)
    return viper_ast.DomainFuncApp(MAP_SET, [ref, idx, value], type, pos, info, MAP_DOMAIN, type_vars)


def map_sum(viper_ast: ViperAST, ref, key_type, pos=None, info=None):
    type_vars = {viper_ast.TypeVar(MAP_KEY_VAR): key_type}
    type = viper_ast.Int
    return viper_ast.DomainFuncApp(MAP_SUM, [ref], type, pos, info, MAP_INT_DOMAIN, type_vars)


def struct_type(viper_ast: ViperAST, struct_type: StructType):
    return viper_ast.DomainType(struct_name(struct_type.name), {}, [])


def struct_field(viper_ast: ViperAST, ref, idx, struct_type: StructType, pos=None, info=None):
    struct = struct_name(struct_type.name)
    field_name = struct_field_name(struct_type.name)
    int = viper_ast.Int
    return viper_ast.DomainFuncApp(field_name, [ref, idx], int, pos, info, struct)


def struct_init(viper_ast: ViperAST, args, struct: StructType, pos=None, info=None):
    domain = struct_name(struct.name)
    init_name = struct_init_name(struct.name)
    return viper_ast.DomainFuncApp(init_name, args, struct_type(viper_ast, struct), pos, info, domain)


def struct_get(viper_ast: ViperAST, ref, member: str, member_type, struct_type: StructType, pos=None, info=None):
    struct = struct_name(struct_type.name)
    idx = viper_ast.IntLit(struct_type.member_indices[member])
    field = struct_field(viper_ast, ref, idx, struct_type, pos, info)
    getter = struct_member_getter_name(struct_type.name, member)
    return viper_ast.DomainFuncApp(getter, [field], member_type, pos, info, struct)


def struct_set(viper_ast: ViperAST, ref, val, member: str, type: StructType, pos=None, info=None):
    setter = struct_member_setter_name(type.name, member)
    s_type = struct_type(viper_ast, type)
    s_name = struct_name(type.name)
    return viper_ast.DomainFuncApp(setter, [ref, val], s_type, pos, info, s_name)
