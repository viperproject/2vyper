"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import ast

from twovyper.ast import names
from twovyper.ast import types
from twovyper.ast.types import FunctionType, MapType, StructType, AnyStructType
from twovyper.ast.nodes import VyperFunction

from twovyper.analysis.analyzer import FunctionAnalysis

from twovyper.viper.ast import ViperAST

from twovyper.translation import mangled
from twovyper.translation.context import Context

from twovyper.utils import first_index


# Helper functions

def init_function() -> ast.FunctionDef:
    type = FunctionType([], None)
    function = VyperFunction(mangled.INIT, {}, type, [], [], [names.PUBLIC], None)
    function.analysis = FunctionAnalysis()
    return function


def msg_var(viper_ast: ViperAST, pos=None, info=None):
    return viper_ast.LocalVarDecl(mangled.MSG, viper_ast.Ref, pos, info)


def msg_sender(viper_ast: ViperAST, ctx: Context, pos=None, info=None):
    msg_var = ctx.msg_var.local_var(ctx)
    type = types.MSG_TYPE
    return struct_get(viper_ast, msg_var, names.MSG_SENDER, viper_ast.Int, type, pos, info)


def msg_value(viper_ast: ViperAST, ctx: Context, pos=None, info=None):
    msg_var = ctx.msg_var.local_var(ctx)
    type = types.MSG_TYPE
    return struct_get(viper_ast, msg_var, names.MSG_VALUE, viper_ast.Int, type, pos, info)


def overflow_var(viper_ast: ViperAST, pos=None, info=None):
    return viper_ast.LocalVarDecl(mangled.OVERFLOW, viper_ast.Bool, pos, info)


def out_of_gas_var(viper_ast: ViperAST, pos=None, info=None):
    return viper_ast.LocalVarDecl(mangled.OUT_OF_GAS, viper_ast.Bool, pos, info)


def msg_sender_call_fail_var(viper_ast: ViperAST, pos=None, info=None):
    return viper_ast.LocalVarDecl(mangled.MSG_SENDER_CALL_FAIL, viper_ast.Bool, pos, info)


def first_public_state_var(viper_ast: ViperAST, pos=None, info=None):
    return viper_ast.LocalVarDecl(mangled.FIRST_PUBLIC_STATE, viper_ast.Bool, pos, info)


def contracts_type():
    return MapType(types.VYPER_ADDRESS, AnyStructType())


def self_address(viper_ast: ViperAST, pos=None, info=None):
    address = mangled.SELF_ADDRESS
    domain = mangled.CONTRACT_DOMAIN
    return viper_ast.DomainFuncApp(address, [], viper_ast.Int, pos, info, domain)


def implements(viper_ast: ViperAST, address, interface: str, ctx: Context, pos=None, info=None):
    impl = mangled.IMPLEMENTS
    domain = mangled.CONTRACT_DOMAIN
    intf = viper_ast.IntLit(first_index(lambda i: i == interface, ctx.program.interfaces), pos)
    return viper_ast.DomainFuncApp(impl, [address, intf], viper_ast.Bool, pos, info, domain)


def div(viper_ast: ViperAST, dividend, divisor, pos=None, info=None):
    # We need a special division function because Vyper uses truncating division
    # instead of Viper's floor division
    mdiv = mangled.MATH_DIV
    domain = mangled.MATH_DOMAIN
    # We pass the Viper floor division as a third argument to trigger a correct
    # division by 0 error instead of an assertion failure if divisor == 0
    args = [dividend, divisor, viper_ast.Div(dividend, divisor, pos)]
    return viper_ast.DomainFuncApp(mdiv, args, viper_ast.Int, pos, info, domain)


def mod(viper_ast: ViperAST, dividend, divisor, pos=None, info=None):
    # We need a special mod function because Vyper uses truncating division
    # instead of Viper's floor division
    mmod = mangled.MATH_MOD
    domain = mangled.MATH_DOMAIN
    # We pass the Viper floor division as a third argument to trigger a correct
    # division by 0 error instead of an assertion failure if divisor == 0
    args = [dividend, divisor, viper_ast.Mod(dividend, divisor, pos)]
    return viper_ast.DomainFuncApp(mmod, args, viper_ast.Int, pos, info, domain)


def pow(viper_ast: ViperAST, base, exp, pos=None, info=None):
    mpow = mangled.MATH_POW
    domain = mangled.MATH_DOMAIN
    return viper_ast.DomainFuncApp(mpow, [base, exp], viper_ast.Int, pos, info, domain)


def sqrt(viper_ast: ViperAST, dec, pos=None, info=None):
    msqrt = mangled.MATH_SQRT
    domain = mangled.MATH_DOMAIN
    return viper_ast.DomainFuncApp(msqrt, [dec], viper_ast.Int, pos, info, domain)


def floor(viper_ast: ViperAST, dec, scaling_factor: int, pos=None, info=None):
    mfloor = mangled.MATH_FLOOR
    domain = mangled.MATH_DOMAIN
    scaling_factor_lit = viper_ast.IntLit(scaling_factor, pos)
    args = [dec, scaling_factor_lit]
    return viper_ast.DomainFuncApp(mfloor, args, viper_ast.Int, pos, info, domain)


def ceil(viper_ast: ViperAST, dec, scaling_factor: int, pos=None, info=None):
    mceil = mangled.MATH_CEIL
    domain = mangled.MATH_DOMAIN
    scaling_factor_lit = viper_ast.IntLit(scaling_factor, pos)
    args = [dec, scaling_factor_lit]
    return viper_ast.DomainFuncApp(mceil, args, viper_ast.Int, pos, info, domain)


def array_type(viper_ast: ViperAST, element_type):
    return viper_ast.SeqType(element_type)


def empty_array(viper_ast: ViperAST, element_type, pos=None, info=None):
    return viper_ast.EmptySeq(element_type, pos, info)


def array_init(viper_ast: ViperAST, arg, size: int, element_type, pos=None, info=None):
    arr_type = array_type(viper_ast, element_type)
    type_vars = {viper_ast.TypeVar(mangled.ARRAY_ELEMENT_VAR): element_type}
    size = viper_ast.IntLit(size, pos, info)
    init = mangled.ARRAY_INIT
    domain = mangled.ARRAY_DOMAIN
    return viper_ast.DomainFuncApp(init, [arg, size], arr_type, pos, info, domain, type_vars)


def array_keccak256(viper_ast: ViperAST, arg, pos=None, info=None):
    int_array_type = viper_ast.SeqType(viper_ast.Int)
    keccak = mangled.ARRAY_KECCAK256
    domain = mangled.ARRAY_INT_DOMAIN
    return viper_ast.DomainFuncApp(keccak, [arg], int_array_type, pos, info, domain)


def array_sha256(viper_ast: ViperAST, arg, pos=None, info=None):
    int_array_type = viper_ast.SeqType(viper_ast.Int)
    sha = mangled.ARRAY_SHA256
    domain = mangled.ARRAY_INT_DOMAIN
    return viper_ast.DomainFuncApp(sha, [arg], int_array_type, pos, info, domain)


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
    key = viper_ast.TypeVar(mangled.MAP_KEY_VAR)
    value = viper_ast.TypeVar(mangled.MAP_VALUE_VAR)
    return {key: key_type, value: value_type}


def map_type(viper_ast: ViperAST, key_type, value_type):
    type_vars = _map_type_var_map(viper_ast, key_type, value_type)
    return viper_ast.DomainType(mangled.MAP_DOMAIN, type_vars, type_vars.keys())


def map_init(viper_ast: ViperAST, arg, key_type, value_type, pos=None, info=None):
    mp_type = map_type(viper_ast, key_type, value_type)
    type_vars = _map_type_var_map(viper_ast, key_type, value_type)
    init = mangled.MAP_INIT
    domain = mangled.MAP_DOMAIN
    return viper_ast.DomainFuncApp(init, [arg], mp_type, pos, info, domain, type_vars)


def map_eq(viper_ast: ViperAST, left, right, key_type, value_type, pos=None, info=None):
    type_vars = _map_type_var_map(viper_ast, key_type, value_type)
    eq = mangled.MAP_EQ
    domain = mangled.MAP_DOMAIN
    return viper_ast.DomainFuncApp(eq, [left, right], viper_ast.Bool, pos, info, domain, type_vars)


def map_get(viper_ast: ViperAST, ref, idx, key_type, value_type, pos=None, info=None):
    type_vars = _map_type_var_map(viper_ast, key_type, value_type)
    get = mangled.MAP_GET
    domain = mangled.MAP_DOMAIN
    return viper_ast.DomainFuncApp(get, [ref, idx], value_type, pos, info, domain, type_vars)


def map_set(viper_ast: ViperAST, ref, idx, value, key_type, value_type, pos=None, info=None):
    type_vars = _map_type_var_map(viper_ast, key_type, value_type)
    mtype = map_type(viper_ast, key_type, value_type)
    mset = mangled.MAP_SET
    domain = mangled.MAP_DOMAIN
    return viper_ast.DomainFuncApp(mset, [ref, idx, value], mtype, pos, info, domain, type_vars)


def map_sum(viper_ast: ViperAST, ref, key_type, pos=None, info=None):
    type_vars = {viper_ast.TypeVar(mangled.MAP_KEY_VAR): key_type}
    type = viper_ast.Int
    msum = mangled.MAP_SUM
    domain = mangled.MAP_INT_DOMAIN
    return viper_ast.DomainFuncApp(msum, [ref], type, pos, info, domain, type_vars)


def struct_type(viper_ast: ViperAST):
    return viper_ast.DomainType(mangled.STRUCT_DOMAIN, {}, [])


def struct_loc(viper_ast: ViperAST, ref, idx, pos=None, info=None):
    domain = mangled.STRUCT_DOMAIN
    loc = mangled.STRUCT_LOC
    return viper_ast.DomainFuncApp(loc, [ref, idx], viper_ast.Int, pos, info, domain)


def struct_init(viper_ast: ViperAST, args, struct: StructType, pos=None, info=None):
    domain = mangled.struct_name(struct.name)
    init_name = mangled.struct_init_name(struct.name)
    type = struct_type(viper_ast)
    return viper_ast.DomainFuncApp(init_name, args, type, pos, info, domain)


def struct_eq(viper_ast: ViperAST, left, right, struct: StructType, pos=None, info=None):
    domain = mangled.struct_name(struct.name)
    eq = mangled.struct_eq_name(struct.name)
    return viper_ast.DomainFuncApp(eq, [left, right], viper_ast.Bool, pos, info, domain)


def _struct_type_var_map(viper_ast: ViperAST, member_type):
    member = viper_ast.TypeVar(mangled.STRUCT_OPS_VALUE_VAR)
    return {member: member_type}


def struct_get(viper_ast: ViperAST, ref, member: str, member_type, struct_type: StructType, pos=None, info=None):
    domain = mangled.STRUCT_OPS_DOMAIN
    idx = viper_ast.IntLit(struct_type.member_indices[member])
    field = struct_loc(viper_ast, ref, idx, pos, info)
    getter = mangled.STRUCT_GET
    type_map = _struct_type_var_map(viper_ast, member_type)
    return viper_ast.DomainFuncApp(getter, [field], member_type, pos, info, domain, type_map)


def struct_set(viper_ast: ViperAST, ref, val, member: str, member_type, type: StructType, pos=None, info=None):
    setter = mangled.STRUCT_SET
    s_type = struct_type(viper_ast)
    domain = mangled.STRUCT_OPS_DOMAIN
    idx = viper_ast.IntLit(type.member_indices[member])
    type_map = _struct_type_var_map(viper_ast, member_type)
    return viper_ast.DomainFuncApp(setter, [ref, idx, val], s_type, pos, info, domain, type_map)


def range(viper_ast: ViperAST, start, end, pos=None, info=None):
    range_func = mangled.RANGE_RANGE
    range_type = viper_ast.SeqType(viper_ast.Int)
    domain = mangled.RANGE_DOMAIN
    return viper_ast.DomainFuncApp(range_func, [start, end], range_type, pos, info, domain)


def ghost_function(viper_ast: ViperAST, name, address, struct, args, return_type, pos=None, info=None):
    ghost_func = mangled.ghost_function_name(name)
    return viper_ast.FuncApp(ghost_func, [address, struct, *args], pos, info, return_type)
