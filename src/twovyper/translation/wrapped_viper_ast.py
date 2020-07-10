"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import functools
import inspect
from itertools import chain
from typing import List
from collections.abc import Iterable

from twovyper.translation import helpers

from twovyper.viper.ast import ViperAST


def wrapped_integer_decorator(possible_wrapped_integer_inputs: List[str], wrap_output=False):
    def _decorator(func):
        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            _self = args[0]
            wrapped_int_type = helpers.wrapped_int_type(_self.viper_ast)
            (arg_names, _, _, _, _, _, _) = inspect.getfullargspec(func)
            had_wrapped_integers = wrap_output
            pos = None
            info = None
            for arg_name, arg in chain(zip(arg_names, args), kwargs):
                if arg_name == "position" or arg_name == "pos":
                    assert pos is None
                    pos = arg
                elif arg_name == "info":
                    info = arg
            # Unwrap wrapped integers
            new_args = []
            for arg_name, arg in zip(arg_names, args):
                new_arg = arg
                if arg_name in possible_wrapped_integer_inputs:
                    if isinstance(arg, Iterable):
                        new_arg = []
                        for a in arg:
                            new_a = a
                            if False if not hasattr(a, 'isSubtype') else a.isSubtype(wrapped_int_type):
                                new_a = helpers.w_unwrap(_self.viper_ast, a, pos, info)
                                had_wrapped_integers = True
                            new_arg.append(new_a)
                    else:
                        if False if not hasattr(arg, 'isSubtype') else arg.isSubtype(wrapped_int_type):
                            new_arg = helpers.w_unwrap(_self.viper_ast, arg, pos, info)
                            had_wrapped_integers = True
                new_args.append(new_arg)
            new_kwargs = {}
            for arg_name, arg in kwargs.items():
                new_arg = arg
                if arg_name in possible_wrapped_integer_inputs:
                    if isinstance(arg, Iterable):
                        new_arg = []
                        for a in arg:
                            new_a = a
                            if False if not hasattr(a, 'isSubtype') else a.isSubtype(wrapped_int_type):
                                new_a = helpers.w_unwrap(_self.viper_ast, a, pos, info)
                                had_wrapped_integers = True
                            new_arg.append(new_a)
                    else:
                        if False if not hasattr(arg, 'isSubtype') else arg.isSubtype(wrapped_int_type):
                            new_arg = helpers.w_unwrap(_self.viper_ast, arg, pos, info)
                            had_wrapped_integers = True
                new_kwargs[arg_name] = new_arg
            # Call ast function
            value = func(*new_args, **new_kwargs)
            # Wrap output if one or more inputs were wrapped
            if had_wrapped_integers:
                if False if not hasattr(value, 'isSubtype') else value.isSubtype(_self.viper_ast.Int):
                    value = helpers.w_wrap(_self.viper_ast, value, pos, info)
            return value

        return _wrapper

    return _decorator


class WrappedViperAST(ViperAST):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast.jvm)
        self.viper_ast = viper_ast

    @wrapped_integer_decorator(["args"])
    def PredicateAccess(self, args, pred_name, position=None, info=None):
        return super().PredicateAccess(args, pred_name, position, info)

    @wrapped_integer_decorator(["args"])
    def DomainFuncApp(self, func_name, args, type_passed, position, info, domain_name, type_var_map=None):
        if type_var_map is None:
            type_var_map = {}
        return super().DomainFuncApp(func_name, args, type_passed, position, info, domain_name, type_var_map)

    @wrapped_integer_decorator(["expr"])
    def Minus(self, expr, position=None, info=None):
        return super().Minus(expr, position, info)

    @wrapped_integer_decorator(["then", "els"])
    def CondExp(self, cond, then, els, position=None, info=None):
        return super().CondExp(cond, then, els, position, info)

    @wrapped_integer_decorator(["left", "right"])
    def EqCmp(self, left, right, position=None, info=None):
        return super().EqCmp(left, right, position, info)

    @wrapped_integer_decorator(["left", "right"])
    def NeCmp(self, left, right, position=None, info=None):
        return super().NeCmp(left, right, position, info)

    @wrapped_integer_decorator(["left", "right"])
    def GtCmp(self, left, right, position=None, info=None):
        return super().GtCmp(left, right, position, info)

    @wrapped_integer_decorator(["left", "right"])
    def GeCmp(self, left, right, position=None, info=None):
        return super().GeCmp(left, right, position, info)

    @wrapped_integer_decorator(["left", "right"])
    def LtCmp(self, left, right, position=None, info=None):
        return super().LtCmp(left, right, position, info)

    @wrapped_integer_decorator(["left", "right"])
    def LeCmp(self, left, right, position=None, info=None):
        return super().LeCmp(left, right, position, info)

    @wrapped_integer_decorator(["args"], True)
    def FuncApp(self, name, args, position=None, info=None, vtype=None):
        return super().FuncApp(name, args, position, info, vtype)

    @wrapped_integer_decorator(["right"])
    def SeqAppend(self, left, right, position=None, info=None):
        return super().SeqAppend(left, right, position, info)

    @wrapped_integer_decorator(["elem"])
    def SeqContains(self, elem, s, position=None, info=None):
        return super().SeqContains(elem, s, position, info)

    @wrapped_integer_decorator(["ind"])
    def SeqIndex(self, s, ind, position=None, info=None):
        return super().SeqIndex(s, ind, position, info)

    @wrapped_integer_decorator(["end"])
    def SeqTake(self, s, end, position=None, info=None):
        return super().SeqTake(s, end, position, info)

    @wrapped_integer_decorator(["end"])
    def SeqDrop(self, s, end, position=None, info=None):
        return super().SeqDrop(s, end, position, info)

    @wrapped_integer_decorator(["ind", "elem"])
    def SeqUpdate(self, s, ind, elem, position=None, info=None):
        return super().SeqUpdate(s, ind, elem, position, info)

    @wrapped_integer_decorator(["left", "right"])
    def Add(self, left, right, position=None, info=None):
        return super().Add(left, right, position, info)

    @wrapped_integer_decorator(["left", "right"])
    def Sub(self, left, right, position=None, info=None):
        return super().Sub(left, right, position, info)

    @wrapped_integer_decorator(["left", "right"])
    def Mul(self, left, right, position=None, info=None):
        return super().Mul(left, right, position, info)

    @wrapped_integer_decorator(["left", "right"])
    def Div(self, left, right, position=None, info=None):
        return super().Div(left, right, position, info)

    @wrapped_integer_decorator(["left", "right"])
    def Mod(self, left, right, position=None, info=None):
        return super().Mod(left, right, position, info)
