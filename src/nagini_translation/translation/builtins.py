"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from nagini_translation.lib.viper_ast import ViperAST

from nagini_translation.ast.nodes import VyperFunction


INIT = '__init__'
SELF = 'self'

MSG = 'msg'
MSG_SENDER = 'sender'


MAP_DOMAIN = '$Map'
MAP_KEY_VAR = '$K'
MAP_VALUE_VAR = '$V'

MAP_INIT = '$map_init'
MAP_GET = '$map_get'
MAP_SET = '$map_set'


def init_function() -> ast.FunctionDef:
    node = ast.FunctionDef(INIT, [], [], [], None)
    return VyperFunction(INIT, {}, {}, None, [], [], ['public'], node)

def self_var(viper_ast: ViperAST, pos, info):
    return viper_ast.LocalVarDecl(SELF, viper_ast.Ref, pos, info)

def msg_var(viper_ast: ViperAST, pos, info):
    return viper_ast.LocalVarDecl(MSG, viper_ast.Ref, pos, info)

def msg_sender_field(viper_ast: ViperAST, pos, info):
    return viper_ast.Field(MSG_SENDER, viper_ast.Int, pos, info)


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
 