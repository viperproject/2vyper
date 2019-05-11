"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from nagini_translation.lib.viper_ast import ViperAST

from nagini_translation.ast import names
from nagini_translation.ast.types import FunctionType
from nagini_translation.ast.nodes import VyperFunction


# Constants for names in translated AST


INIT = names.INIT
SELF = names.SELF

MSG = names.MSG
MSG_SENDER = names.MSG_SENDER
MSG_VALUE = names.MSG_VALUE

BLOCK = names.BLOCK
BLOCK_TIMESTAMP = names.BLOCK_TIMESTAMP

RESULT_VAR = '$res'
SUCCESS_VAR = '$succ'

END_LABEL = 'end'
REVERT_LABEL = 'revert'

ARRAY_DOMAIN = '$Array'
ARRAY_ELEMENT_VAR = '$E'

ARRAY_INIT = '$array_init'

MAP_DOMAIN = '$Map'
MAP_INT_DOMAIN = '$MapInt'
MAP_KEY_VAR = '$K'
MAP_VALUE_VAR = '$V'

MAP_INIT = '$map_init'
MAP_GET = '$map_get'
MAP_SET = '$map_set'
MAP_SUM = '$map_sum'


def init_function() -> ast.FunctionDef:
    node = ast.FunctionDef(INIT, [], [], [], None)
    type = FunctionType([], None)
    return VyperFunction(INIT, {}, {}, type, [], [], [names.PUBLIC], node)

def self_var(viper_ast: ViperAST, pos = None, info = None):
    return viper_ast.LocalVarDecl(SELF, viper_ast.Ref, pos, info)

def msg_var(viper_ast: ViperAST, pos = None, info = None):
    return viper_ast.LocalVarDecl(MSG, viper_ast.Ref, pos, info)

def msg_sender_field(viper_ast: ViperAST, pos = None, info = None):
    return viper_ast.Field(MSG_SENDER, viper_ast.Int, pos, info)

def msg_value_field(viper_ast: ViperAST, pos = None, info = None):
    return viper_ast.Field(MSG_VALUE, viper_ast.Int, pos, info)

def block_var(viper_ast: ViperAST, pos = None, info = None):
     return viper_ast.LocalVarDecl(BLOCK, viper_ast.Ref, pos, info)

def block_timestamp_field(viper_ast: ViperAST, pos = None, info = None):
     return viper_ast.Field(BLOCK_TIMESTAMP, viper_ast.Int, pos, info)

def ret_var(viper_ast: ViperAST, ret_type, pos = None, info = None):
     return viper_ast.LocalVarDecl(RESULT_VAR, ret_type, pos, info)

def success_var(viper_ast: ViperAST, pos = None, info = None):
     return viper_ast.LocalVarDecl(SUCCESS_VAR, viper_ast.Bool, pos, info)

def end_label(viper_ast: ViperAST, pos = None, info = None):
     return viper_ast.Label(END_LABEL, pos, info)

def revert_label(viper_ast: ViperAST, pos = None, info = None):
     return viper_ast.Label(REVERT_LABEL, pos, info)

def array_type(viper_ast: ViperAST, element_type):
     return viper_ast.SeqType(element_type)

def array_init(viper_ast: ViperAST, arg, size: int, element_type, pos = None, info = None):
     arr_type = array_type(viper_ast, element_type)
     type_vars = {viper_ast.TypeVar(ARRAY_ELEMENT_VAR): element_type}
     size = viper_ast.IntLit(size, pos, info)
     return viper_ast.DomainFuncApp(ARRAY_INIT, [arg, size], arr_type, pos, info, ARRAY_DOMAIN, type_vars)

def array_length(viper_ast: ViperAST, ref, pos = None, info = None):
     return viper_ast.SeqLength(ref, pos, info)

def array_get(viper_ast: ViperAST, ref, idx, element_type, pos = None, info = None):
     return viper_ast.SeqIndex(ref, idx, pos, info)

def array_set(viper_ast: ViperAST, ref, idx, value, element_type, pos = None, info = None):
     return viper_ast.SeqUpdate(ref, idx, value, pos, info)

def array_contains(viper_ast: ViperAST, value, ref, pos = None, info = None):
     return viper_ast.SeqContains(value, ref, pos, info)

def array_not_contains(viper_ast: ViperAST, value, ref, pos = None, info = None):
     return viper_ast.Not(array_contains(viper_ast, value, ref, pos, info), pos, info)

def _map_type_var_map(viper_ast: ViperAST, key_type, value_type):
    key = viper_ast.TypeVar(MAP_KEY_VAR)
    value = viper_ast.TypeVar(MAP_VALUE_VAR)
    return {key: key_type, value: value_type}

def map_type(viper_ast: ViperAST, key_type, value_type):
    type_vars = _map_type_var_map(viper_ast, key_type, value_type)
    return viper_ast.DomainType(MAP_DOMAIN, type_vars, type_vars.keys())

def map_init(viper_ast: ViperAST, arg, key_type, value_type, pos = None, info = None):
    mp_type = map_type(viper_ast, key_type, value_type)
    type_vars = _map_type_var_map(viper_ast, key_type, value_type)
    return viper_ast.DomainFuncApp(MAP_INIT, [arg], mp_type, pos, info, MAP_DOMAIN, type_vars)

def map_get(viper_ast: ViperAST, ref, idx, key_type, value_type, pos = None, info = None):
    type_vars = _map_type_var_map(viper_ast, key_type, value_type)
    return viper_ast.DomainFuncApp(MAP_GET, [ref, idx], value_type, pos, info, MAP_DOMAIN, type_vars)

def map_set(viper_ast: ViperAST, ref, idx, value, key_type, value_type, pos = None, info = None):
    type_vars = _map_type_var_map(viper_ast, key_type, value_type)
    type = map_type(viper_ast, key_type, value_type)
    return viper_ast.DomainFuncApp(MAP_SET, [ref, idx, value], type, pos, info, MAP_DOMAIN, type_vars)
 
def map_sum(viper_ast: ViperAST, ref, key_type, pos = None, info = None):
     type_vars = {viper_ast.TypeVar(MAP_KEY_VAR): key_type}
     type = viper_ast.Int
     return viper_ast.DomainFuncApp(MAP_SUM, [ref], type, pos, info, MAP_INT_DOMAIN, type_vars)