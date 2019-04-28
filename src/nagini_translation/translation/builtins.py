"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from nagini_translation.lib.viper_ast import ViperAST

from nagini_translation.parsing.ast import VyperFunction


INIT = '__init__'
SELF = 'self'

MIN = 'min'
MAX = 'max'

MAP_ACC = '$map'
MAP_INIT = '$map_init'
MAP_GET = '$map_get'
MAP_SET = '$map_set'


def init_function() -> ast.FunctionDef:
    node = ast.FunctionDef(INIT, [], [], [], None)
    return VyperFunction(INIT, {}, {}, None, [], [], ['public'], node)

def self_var(viper_ast: ViperAST, pos, info):
    return viper_ast.LocalVarDecl(SELF, viper_ast.Ref, pos, info)


def map_acc_field(viper_ast: ViperAST, pos, info):
    return viper_ast.Field(MAP_ACC, viper_ast.Int, pos, info)

def map_acc(viper_ast: ViperAST, ref, pos, info):
    fa = viper_ast.FieldAccess(ref, map_acc_field(viper_ast, pos, info), pos, info)
    return viper_ast.FieldAccessPredicate(fa, viper_ast.FullPerm(pos, info), pos, info)

def map_get(viper_ast: ViperAST, ref, idx, pos, info):
    return viper_ast.FuncApp(MAP_GET, [ref, idx], pos, info, viper_ast.Int)

def map_set(viper_ast: ViperAST, ref, idx, value, pos, info):
    return viper_ast.MethodCall(MAP_SET, [ref, idx, value], [], pos, info)
 