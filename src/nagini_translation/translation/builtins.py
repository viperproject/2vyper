"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from nagini_translation.lib.viper_ast import ViperAST

from nagini_translation.ast import names
from nagini_translation.ast.nodes import VyperFunction


# Constants for names in translated AST


INIT = names.INIT
SELF = names.SELF

MSG = names.MSG
MSG_SENDER = names.MSG_SENDER

RESULT_VAR = '$res'
SUCCESS_VAR = '$succ'

END_LABEL = 'end'
REVERT_LABEL = 'revert'

MAP_DOMAIN = '$Map'
MAP_SUM_DOMAIN = '$MapSum'
MAP_UINT_DOMAIN = '$MapUInt'
MAP_KEY_VAR = '$K'
MAP_VALUE_VAR = '$V'

MAP_INIT = '$map_init'
MAP_GET = '$map_get'
MAP_SET = '$map_set'
MAP_SUM = '$map_sum'
MAP_GET_UINT = '$map_get_uint'
MAP_SUM_UINT = '$map_sum_uint'


def init_function() -> ast.FunctionDef:
    node = ast.FunctionDef(INIT, [], [], [], None)
    return VyperFunction(INIT, {}, {}, None, [], [], [names.PUBLIC], node)

def self_var(viper_ast: ViperAST, pos, info):
    return viper_ast.LocalVarDecl(SELF, viper_ast.Ref, pos, info)

def msg_var(viper_ast: ViperAST, pos, info):
    return viper_ast.LocalVarDecl(MSG, viper_ast.Ref, pos, info)

def msg_sender_field(viper_ast: ViperAST, pos, info):
    return viper_ast.Field(MSG_SENDER, viper_ast.Int, pos, info)

def ret_var(viper_ast: ViperAST, ret_type, pos, info):
     return viper_ast.LocalVarDecl(RESULT_VAR, ret_type, pos, info)

def success_var(viper_ast: ViperAST, pos, info):
     return viper_ast.LocalVarDecl(SUCCESS_VAR, viper_ast.Bool, pos, info)

def end_label(viper_ast: ViperAST, pos, info):
     return viper_ast.Label(END_LABEL, pos, info)

def revert_label(viper_ast: ViperAST, pos, info):
     return viper_ast.Label(REVERT_LABEL, pos, info)

def _map_type_var_map(viper_ast: ViperAST, key_type, value_type):
    key = viper_ast.TypeVar(MAP_KEY_VAR)
    value = viper_ast.TypeVar(MAP_VALUE_VAR)
    return {key: key_type, value: value_type}

def map_type(viper_ast: ViperAST, key_type, value_type):
    type_vars = _map_type_var_map(viper_ast, key_type, value_type)
    return viper_ast.DomainType(MAP_DOMAIN, type_vars, list(type_vars.keys()))

def map_init(viper_ast: ViperAST, arg, key_type, value_type, pos, info):
    mp_type = map_type(viper_ast, key_type, value_type)
    type_vars = _map_type_var_map(viper_ast, key_type, value_type)
    return viper_ast.DomainFuncApp(MAP_INIT, [arg], mp_type, pos, info, MAP_DOMAIN, type_vars)

def map_get(viper_ast: ViperAST, ref, idx, key_type, value_type, pos, info):
    type_vars = _map_type_var_map(viper_ast, key_type, value_type)
    return viper_ast.DomainFuncApp(MAP_GET, [ref, idx], value_type, pos, info, MAP_DOMAIN, type_vars)

def map_set(viper_ast: ViperAST, ref, idx, value, key_type, value_type, pos, info):
    type_vars = _map_type_var_map(viper_ast, key_type, value_type)
    type = map_type(viper_ast, key_type, value_type)
    return viper_ast.DomainFuncApp(MAP_SET, [ref, idx, value], type, pos, info, MAP_DOMAIN, type_vars)
 
def map_sum(viper_ast: ViperAST, ref, key_type, pos, info):
     type_vars = {viper_ast.TypeVar(MAP_KEY_VAR): key_type}
     type = viper_ast.Int
     return viper_ast.DomainFuncApp(MAP_SUM, [ref], type, pos, info, MAP_SUM_DOMAIN, type_vars)

def map_get_uint(viper_ast: ViperAST, ref, idx, key_type, pos, info):
     type_vars = {viper_ast.TypeVar(MAP_KEY_VAR): key_type}
     type = viper_ast.Int
     return viper_ast.DomainFuncApp(MAP_GET_UINT, [ref, idx], type, pos, info, MAP_UINT_DOMAIN, type_vars)

def map_sum_uint(viper_ast: ViperAST, ref, key_type, pos, info):
     type_vars = {viper_ast.TypeVar(MAP_KEY_VAR): key_type}
     type = viper_ast.Int
     return viper_ast.DomainFuncApp(MAP_SUM_UINT, [ref], type, pos, info, MAP_UINT_DOMAIN, type_vars)
