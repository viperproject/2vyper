"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Union

from twovyper.ast import ast_nodes as ast, names, types
from twovyper.ast.types import FunctionType, MapType, StructType, AnyStructType, ResourceType
from twovyper.ast.nodes import VyperFunction, Resource

from twovyper.analysis.analyzer import FunctionAnalysis

from twovyper.viper.ast import ViperAST

from twovyper.translation import mangled
from twovyper.translation.context import Context
from twovyper.translation.wrapped_viper_ast import WrappedViperAST, wrapped_integer_decorator

from twovyper.utils import first_index

from twovyper.viper.typedefs import Expr


# Helper functions

def init_function() -> VyperFunction:
    type = FunctionType([], None)
    function = VyperFunction(mangled.INIT, -1, {}, {}, type, [], [], [], {}, [],
                             [ast.Decorator(names.PUBLIC, [])], None)
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


def call_failed(viper_ast: ViperAST, address, pos=None, info=None):
    write = viper_ast.FullPerm(pos)
    predicate = viper_ast.PredicateAccess([address], mangled.FAILED, pos)
    predicate_acc = viper_ast.PredicateAccessPredicate(predicate, write, pos)
    return viper_ast.Inhale(predicate_acc, pos, info)


def check_call_failed(viper_ast: ViperAST, address, pos=None, info=None):
    none = viper_ast.NoPerm(pos)
    predicate = viper_ast.PredicateAccess([address], mangled.FAILED, pos)
    return viper_ast.GtCmp(viper_ast.CurrentPerm(predicate, pos), none, pos, info)


def first_public_state_var(viper_ast: ViperAST, pos=None, info=None):
    return viper_ast.LocalVarDecl(mangled.FIRST_PUBLIC_STATE, viper_ast.Bool, pos, info)


def contracts_type():
    return MapType(types.VYPER_ADDRESS, AnyStructType())


def allocated_type():
    return MapType(AnyStructType(), MapType(types.VYPER_ADDRESS, types.NON_NEGATIVE_INT))


def offer_type():
    members = {
        '0': types.VYPER_WEI_VALUE,
        '1': types.VYPER_WEI_VALUE,
        '2': types.VYPER_ADDRESS,
        '3': types.VYPER_ADDRESS
    }
    return StructType(mangled.OFFER, members)


def offered_type():
    return MapType(AnyStructType(), MapType(AnyStructType(), MapType(offer_type(), types.NON_NEGATIVE_INT)))


def trusted_type():
    return MapType(types.VYPER_ADDRESS, MapType(types.VYPER_ADDRESS, MapType(types.VYPER_ADDRESS, types.VYPER_BOOL)))


def allocation_predicate(viper_ast: ViperAST, resource, address, pos=None):
    return viper_ast.PredicateAccess([resource, address], mangled.ALLOCATION, pos)


def offer(viper_ast: ViperAST, from_val, to_val, from_addr, to_addr, pos=None):
    return struct_init(viper_ast, [from_val, to_val, from_addr, to_addr], offer_type(), pos)


def offer_predicate(viper_ast: ViperAST, from_resource, to_resource, from_val, to_val, from_addr, to_addr, pos=None):
    return viper_ast.PredicateAccess([from_resource, to_resource, from_val, to_val, from_addr, to_addr], mangled.OFFER, pos)


def no_offers(viper_ast: ViperAST, offered, resource, address, pos=None):
    return viper_ast.FuncApp(mangled.NO_OFFERS, [offered, resource, address], pos, type=viper_ast.Bool)


def trust_predicate(viper_ast: ViperAST, where, address, by_address, pos=None):
    return viper_ast.PredicateAccess([where, address, by_address], mangled.TRUST, pos)


def trust_no_one(viper_ast: ViperAST, trusted, who, where, pos=None):
    return viper_ast.FuncApp(mangled.TRUST_NO_ONE, [trusted, who, where], pos, type=viper_ast.Bool)


def performs_predicate(viper_ast: ViperAST, function: str, args, pos=None):
    name = mangled.performs_predicate_name(function)
    return viper_ast.PredicateAccess(args, name, pos)


def creator_resource() -> Resource:
    creator_name = mangled.CREATOR
    creator_type = ResourceType(creator_name, {mangled.CREATOR_RESOURCE: AnyStructType()})
    return Resource(creator_type, None, None)


def blockhash(viper_ast: ViperAST, no, ctx: Context, pos=None, info=None):
    bhash = mangled.BLOCKCHAIN_BLOCKHASH
    domain = mangled.BLOCKCHAIN_DOMAIN
    return viper_ast.DomainFuncApp(bhash, [no], viper_ast.SeqType(viper_ast.Int), pos, info, domain)


def method_id(viper_ast: ViperAST, method, len: int, pos=None, info=None):
    mid = mangled.BLOCKCHAIN_METHOD_ID
    domain = mangled.BLOCKCHAIN_DOMAIN
    rl = viper_ast.IntLit(len, pos)
    return viper_ast.DomainFuncApp(mid, [method, rl], viper_ast.SeqType(viper_ast.Int), pos, info, domain)


def keccak256(viper_ast: ViperAST, arg, pos=None, info=None):
    int_array_type = viper_ast.SeqType(viper_ast.Int)
    keccak = mangled.BLOCKCHAIN_KECCAK256
    domain = mangled.BLOCKCHAIN_DOMAIN
    return viper_ast.DomainFuncApp(keccak, [arg], int_array_type, pos, info, domain)


def sha256(viper_ast: ViperAST, arg, pos=None, info=None):
    int_array_type = viper_ast.SeqType(viper_ast.Int)
    sha = mangled.BLOCKCHAIN_SHA256
    domain = mangled.BLOCKCHAIN_DOMAIN
    return viper_ast.DomainFuncApp(sha, [arg], int_array_type, pos, info, domain)


def ecrecover(viper_ast: ViperAST, args, pos=None, info=None):
    ec = mangled.BLOCKCHAIN_ECRECOVER
    domain = mangled.BLOCKCHAIN_DOMAIN
    return viper_ast.DomainFuncApp(ec, args, viper_ast.Int, pos, info, domain)


def ecadd(viper_ast: ViperAST, args, pos=None, info=None):
    int_array_type = viper_ast.SeqType(viper_ast.Int)
    ea = mangled.BLOCKCHAIN_ECADD
    domain = mangled.BLOCKCHAIN_DOMAIN
    return viper_ast.DomainFuncApp(ea, args, int_array_type, pos, info, domain)


def ecmul(viper_ast: ViperAST, args, pos=None, info=None):
    int_array_type = viper_ast.SeqType(viper_ast.Int)
    em = mangled.BLOCKCHAIN_ECMUL
    domain = mangled.BLOCKCHAIN_DOMAIN
    return viper_ast.DomainFuncApp(em, args, int_array_type, pos, info, domain)


def self_address(viper_ast: ViperAST, pos=None, info=None):
    address = mangled.SELF_ADDRESS
    domain = mangled.CONTRACT_DOMAIN
    return viper_ast.DomainFuncApp(address, [], viper_ast.Int, pos, info, domain)


def implements(viper_ast: ViperAST, address, interface: str, ctx: Context, pos=None, info=None):
    impl = mangled.IMPLEMENTS
    domain = mangled.CONTRACT_DOMAIN
    intf = viper_ast.IntLit(first_index(lambda i: i == interface, ctx.program.interfaces), pos)
    return viper_ast.DomainFuncApp(impl, [address, intf], viper_ast.Bool, pos, info, domain)


def wrapped_int_type(viper_ast: ViperAST):
    return viper_ast.DomainType(mangled.WRAPPED_INT_DOMAIN, {}, [])


def w_mul(viper_ast: ViperAST, first, second, pos=None, info=None):
    if isinstance(viper_ast, WrappedViperAST):
        viper_ast = viper_ast.viper_ast
    wi_mul = mangled.WRAPPED_INT_MUL
    domain = mangled.WRAPPED_INT_DOMAIN
    args = [first, second]
    return viper_ast.DomainFuncApp(wi_mul, args, wrapped_int_type(viper_ast), pos, info, domain)


def w_div(viper_ast: ViperAST, first, second, pos=None, info=None):
    if isinstance(viper_ast, WrappedViperAST):
        viper_ast = viper_ast.viper_ast
    wi_div = mangled.WRAPPED_INT_DIV
    domain = mangled.WRAPPED_INT_DOMAIN
    args = [first, second]
    func_app = viper_ast.DomainFuncApp(wi_div, args, wrapped_int_type(viper_ast), pos, info, domain)
    is_div_zero = viper_ast.EqCmp(viper_ast.IntLit(0), w_unwrap(viper_ast, second, pos, info), pos, info)
    artificial_div_zero = w_wrap(viper_ast, viper_ast.Div(w_unwrap(viper_ast, first, pos, info),
                                                          w_unwrap(viper_ast, second, pos, info),
                                                          pos, info), pos, info)
    return viper_ast.CondExp(is_div_zero, artificial_div_zero, func_app, pos, info)


def w_mod(viper_ast: ViperAST, first, second, pos=None, info=None):
    if isinstance(viper_ast, WrappedViperAST):
        viper_ast = viper_ast.viper_ast
    wi_mod = mangled.WRAPPED_INT_MOD
    domain = mangled.WRAPPED_INT_DOMAIN
    args = [first, second]
    func_app = viper_ast.DomainFuncApp(wi_mod, args, wrapped_int_type(viper_ast), pos, info, domain)
    is_div_zero = viper_ast.EqCmp(viper_ast.IntLit(0), w_unwrap(viper_ast, second, pos, info), pos, info)
    artificial_div_zero = w_wrap(viper_ast, viper_ast.Mod(w_unwrap(viper_ast, first, pos, info),
                                                          w_unwrap(viper_ast, second, pos, info),
                                                          pos, info), pos, info)
    return viper_ast.CondExp(is_div_zero, artificial_div_zero, func_app, pos, info)


def w_wrap(viper_ast: ViperAST, value, pos=None, info=None):
    if isinstance(viper_ast, WrappedViperAST):
        viper_ast = viper_ast.viper_ast
    wi_wrap = mangled.WRAPPED_INT_WRAP
    domain = mangled.WRAPPED_INT_DOMAIN
    return viper_ast.DomainFuncApp(wi_wrap, [value], wrapped_int_type(viper_ast), pos, info, domain)


def w_unwrap(viper_ast: ViperAST, value, pos=None, info=None):
    if isinstance(viper_ast, WrappedViperAST):
        viper_ast = viper_ast.viper_ast
    wi_unwrap = mangled.WRAPPED_INT_UNWRAP
    domain = mangled.WRAPPED_INT_DOMAIN
    return viper_ast.DomainFuncApp(wi_unwrap, [value], viper_ast.Int, pos, info, domain)


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


def shift(viper_ast: ViperAST, arg, shift, pos=None, info=None):
    b_shift = mangled.MATH_SHIFT
    domain = mangled.MATH_DOMAIN
    return viper_ast.DomainFuncApp(b_shift, [arg, shift], viper_ast.Int, pos, info, domain)


def bitwise_not(viper_ast: ViperAST, arg, pos=None, info=None):
    b_not = mangled.MATH_BITWISE_NOT
    domain = mangled.MATH_DOMAIN
    return viper_ast.DomainFuncApp(b_not, [arg], viper_ast.Int, pos, info, domain)


def bitwise_and(viper_ast: ViperAST, a, b, pos=None, info=None):
    b_and = mangled.MATH_BITWISE_AND
    domain = mangled.MATH_DOMAIN
    return viper_ast.DomainFuncApp(b_and, [a, b], viper_ast.Int, pos, info, domain)


def bitwise_or(viper_ast: ViperAST, a, b, pos=None, info=None):
    b_or = mangled.MATH_BITWISE_OR
    domain = mangled.MATH_DOMAIN
    return viper_ast.DomainFuncApp(b_or, [a, b], viper_ast.Int, pos, info, domain)


def bitwise_xor(viper_ast: ViperAST, a, b, pos=None, info=None):
    b_xor = mangled.MATH_BITWISE_XOR
    domain = mangled.MATH_DOMAIN
    return viper_ast.DomainFuncApp(b_xor, [a, b], viper_ast.Int, pos, info, domain)


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


def array_length(viper_ast: ViperAST, ref, pos=None, info=None):
    return viper_ast.SeqLength(ref, pos, info)


@wrapped_integer_decorator(wrap_output=True)
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


@wrapped_integer_decorator(wrap_output=True)
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
    domain = mangled.struct_name(struct.name, struct.kind)
    init_name = mangled.struct_init_name(struct.name, struct.kind)
    type = struct_type(viper_ast)
    return viper_ast.DomainFuncApp(init_name, args, type, pos, info, domain)


def struct_eq(viper_ast: ViperAST, left, right, struct: StructType, pos=None, info=None):
    domain = mangled.struct_name(struct.name, struct.kind)
    eq = mangled.struct_eq_name(struct.name, struct.kind)
    return viper_ast.DomainFuncApp(eq, [left, right], viper_ast.Bool, pos, info, domain)


def struct_type_tag(viper_ast: ViperAST, ref, pos=None, info=None):
    """
    Returns the type tag of a struct which we store at index -1 of a struct
    """
    domain = mangled.STRUCT_OPS_DOMAIN
    idx = viper_ast.IntLit(mangled.STRUCT_TYPE_LOC)
    field = struct_loc(viper_ast, ref, idx, pos)
    getter = mangled.STRUCT_GET
    type_type = viper_ast.Int
    type_map = _struct_type_var_map(viper_ast, type_type)
    return viper_ast.DomainFuncApp(getter, [field], type_type, pos, info, domain, type_map)


def _struct_type_var_map(viper_ast: ViperAST, member_type):
    member = viper_ast.TypeVar(mangled.STRUCT_OPS_VALUE_VAR)
    return {member: member_type}


@wrapped_integer_decorator(wrap_output=True)
def struct_get(viper_ast: ViperAST, ref, member: str, member_type, struct_type: StructType, pos=None, info=None):
    domain = mangled.STRUCT_OPS_DOMAIN
    idx = viper_ast.IntLit(struct_type.member_indices[member])
    field = struct_loc(viper_ast, ref, idx, pos, info)
    getter = mangled.STRUCT_GET
    type_map = _struct_type_var_map(viper_ast, member_type)
    return viper_ast.DomainFuncApp(getter, [field], member_type, pos, info, domain, type_map)


def struct_pure_get_success(viper_ast: ViperAST, ref, pos=None):
    return struct_get_idx(viper_ast, ref, 0, viper_ast.Bool, pos)


def struct_pure_get_result(viper_ast: ViperAST, ref, viper_type,  pos=None):
    return struct_get_idx(viper_ast, ref, 1, viper_type, pos)


def struct_get_idx(viper_ast: ViperAST, ref, idx: Union[int, Expr], viper_type, pos=None, info=None):
    domain = mangled.STRUCT_OPS_DOMAIN
    idx_lit = viper_ast.IntLit(idx) if isinstance(idx, int) else idx
    field = struct_loc(viper_ast, ref, idx_lit, pos, info)
    getter = mangled.STRUCT_GET
    type_map = _struct_type_var_map(viper_ast, viper_type)
    return viper_ast.DomainFuncApp(getter, [field], viper_type, pos, info, domain, type_map)


def struct_set(viper_ast: ViperAST, ref, val, member: str, member_type, type: StructType, pos=None, info=None):
    setter = mangled.STRUCT_SET
    s_type = struct_type(viper_ast)
    domain = mangled.STRUCT_OPS_DOMAIN
    idx = viper_ast.IntLit(type.member_indices[member])
    type_map = _struct_type_var_map(viper_ast, member_type)
    return viper_ast.DomainFuncApp(setter, [ref, idx, val], s_type, pos, info, domain, type_map)


def struct_set_idx(viper_ast: ViperAST, ref, val, idx: int, member_type, pos=None, info=None):
    setter = mangled.STRUCT_SET
    s_type = struct_type(viper_ast)
    domain = mangled.STRUCT_OPS_DOMAIN
    idx = viper_ast.IntLit(idx)
    type_map = _struct_type_var_map(viper_ast, member_type)
    return viper_ast.DomainFuncApp(setter, [ref, idx, val], s_type, pos, info, domain, type_map)


def get_lock(viper_ast: ViperAST, name: str, ctx: Context, pos=None, info=None):
    lock_name = mangled.lock_name(name)
    self_var = ctx.self_var.local_var(ctx)
    return struct_get(viper_ast, self_var, lock_name, viper_ast.Bool, ctx.self_type, pos, info)


def set_lock(viper_ast: ViperAST, name: str, val: bool, ctx: Context, pos=None, info=None):
    lock_name = mangled.lock_name(name)
    value = viper_ast.TrueLit(pos) if val else viper_ast.FalseLit(pos)
    self_var = ctx.self_var.local_var(ctx)
    return struct_set(viper_ast, self_var, value, lock_name, viper_ast.Bool, ctx.self_type, pos, info)


@wrapped_integer_decorator(wrap_output=True)
def convert_bytes32_to_signed_int(viper_ast: ViperAST, bytes, pos=None, info=None):
    domain = mangled.CONVERT_DOMAIN
    function = mangled.CONVERT_BYTES32_TO_SIGNED_INT
    return viper_ast.DomainFuncApp(function, [bytes], viper_ast.Int, pos, info, domain)


@wrapped_integer_decorator(wrap_output=True)
def convert_bytes32_to_unsigned_int(viper_ast: ViperAST, bytes, pos=None, info=None):
    domain = mangled.CONVERT_DOMAIN
    function = mangled.CONVERT_BYTES32_TO_UNSIGNED_INT
    return viper_ast.DomainFuncApp(function, [bytes], viper_ast.Int, pos, info, domain)


def convert_signed_int_to_bytes32(viper_ast: ViperAST, i, pos=None, info=None):
    domain = mangled.CONVERT_DOMAIN
    function = mangled.CONVERT_SIGNED_INT_TO_BYTES32
    return viper_ast.DomainFuncApp(function, [i], viper_ast.SeqType(viper_ast.Int), pos, info, domain)


def convert_unsigned_int_to_bytes32(viper_ast: ViperAST, i, pos=None, info=None):
    domain = mangled.CONVERT_DOMAIN
    function = mangled.CONVERT_UNSIGNED_INT_TO_BYTES32
    return viper_ast.DomainFuncApp(function, [i], viper_ast.SeqType(viper_ast.Int), pos, info, domain)


def pad32(viper_ast: ViperAST, bytes, pos=None, info=None):
    """
    Left-pads a byte array shorter than 32 bytes with 0s so that its resulting length is 32.
    Left-crops a byte array longer than 32 bytes so that its resulting length is 32.
    """
    domain = mangled.CONVERT_DOMAIN
    function = mangled.CONVERT_PAD32
    return viper_ast.DomainFuncApp(function, [bytes], viper_ast.SeqType(viper_ast.Int), pos, info, domain)


def range(viper_ast: ViperAST, start, end, pos=None, info=None):
    range_func = mangled.RANGE_RANGE
    range_type = viper_ast.SeqType(viper_ast.Int)
    domain = mangled.RANGE_DOMAIN
    return viper_ast.DomainFuncApp(range_func, [start, end], range_type, pos, info, domain)


def ghost_function(viper_ast: ViperAST, function, address, struct, args, return_type, pos=None, info=None):
    ghost_func = mangled.ghost_function_name(function.interface, function.name)
    return viper_ast.FuncApp(ghost_func, [address, struct, *args], pos, info, return_type)


def havoc_var(viper_ast: ViperAST, viper_type, ctx: Context):
    if ctx.is_pure_function:
        pure_idx = ctx.next_pure_var_index()
        function_result = viper_ast.Result(struct_type(viper_ast))
        return struct_get_idx(viper_ast, function_result, pure_idx, viper_type)
    else:
        havoc_name = ctx.new_local_var_name('havoc')
        havoc = viper_ast.LocalVarDecl(havoc_name, viper_type)
        ctx.new_local_vars.append(havoc)
        return havoc.localVar()


def flattened_conditional(viper_ast: ViperAST, cond, thn, els, pos=None):
    res = []

    if_class = viper_ast.ast.If
    seqn_class = viper_ast.ast.Seqn
    assign_class = viper_ast.ast.LocalVarAssign
    assume_or_check_stmts = [viper_ast.ast.Inhale, viper_ast.ast.Assert, viper_ast.ast.Exhale]
    supported_classes = [*assume_or_check_stmts, if_class, seqn_class, assign_class]
    if all(stmt.__class__ in supported_classes for stmt in thn + els):
        not_cond = viper_ast.Not(cond, pos)
        thn = [(stmt, cond) for stmt in thn]
        els = [(stmt, not_cond) for stmt in els]
        for stmt, cond in thn + els:
            stmt_class = stmt.__class__
            if stmt_class in assume_or_check_stmts:
                implies = viper_ast.Implies(cond, stmt.exp(), stmt.pos())
                res.append(stmt_class(implies, stmt.pos(), stmt.info(), stmt.errT()))
            elif stmt_class == assign_class:
                cond_expr = viper_ast.CondExp(cond, stmt.rhs(), stmt.lhs(), stmt.pos())
                res.append(viper_ast.LocalVarAssign(stmt.lhs(), cond_expr, stmt.pos()))
            elif stmt_class == if_class:
                new_cond = viper_ast.And(stmt.cond(), cond, stmt.pos())
                stmts = viper_ast.to_list(stmt.thn().ss())
                res.extend(flattened_conditional(viper_ast, new_cond, stmts, [], stmt.pos()))
                new_cond = viper_ast.And(viper_ast.Not(stmt.cond(), stmt.pos()), cond, stmt.pos())
                stmts = viper_ast.to_list(stmt.els().ss())
                res.extend(flattened_conditional(viper_ast, new_cond, stmts, [], stmt.pos()))
            elif stmt_class == seqn_class:
                seqn_as_list = viper_ast.to_list(stmt.ss())
                transformed_stmts = flattened_conditional(viper_ast, cond, seqn_as_list, [], stmt.pos())
                res.append(viper_ast.Seqn(transformed_stmts, stmt.pos(), stmt.info()))
            else:
                assert False
    else:
        res.append(viper_ast.If(cond, thn, [], pos))
    return res
