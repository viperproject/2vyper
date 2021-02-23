"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import functools
import inspect
from typing import Optional, Union
from collections.abc import Iterable

from twovyper.translation import helpers

from twovyper.viper.ast import ViperAST
from twovyper.viper.typedefs import Expr


def wrapped_integer_decorator(*possible_wrapped_integer_inputs: str, wrap_output=False, store_unwrap_info=True):
    """
    This decorator can be used to automatically unwrap $Int to Int. All functions, predicates, axioms and operators
    on Int are only available to Int and not $Int. With this decorator, all these functions, predicates, axioms and
    operators on Int can also be used for $Int.

    This decorator also stores the information if it unwrapped an expression
    or it wraps a resulting Int again to a $Int.

    :param possible_wrapped_integer_inputs: The names of arguments that may contain $Int typed expressions

    :param wrap_output: A flag if the output should always be considered to be a $Int (Not only if an input was a $Int)

    :param store_unwrap_info: A boolean Flag, if false then the output gets wrapped if the output is considered as
                              a $Int. If true then only the :attr:`WrappedViperAST.unwrapped_some_expressions` flag
                              gets set.
    """
    def _decorator(func):
        (arg_names, _, _, _, _, _, _) = inspect.getfullargspec(func)

        pos_names = {"position", "pos"}
        info_names = {"info"}
        assert pos_names.isdisjoint(possible_wrapped_integer_inputs),\
            'The "position" argument cannot contain wrapped integers.'
        assert info_names.isdisjoint(possible_wrapped_integer_inputs),\
            'The "info" argument cannot contain wrapped integers.'
        assert wrap_output or len(possible_wrapped_integer_inputs) > 0,\
            'The decorator is not necessary here.'

        pos_index = -1
        info_index = -1
        possible_wrapped_integer_inputs_indices = []

        for idx, arg_n in enumerate(arg_names):
            if arg_n in pos_names:
                assert pos_index == -1
                pos_index = idx
            elif arg_n in info_names:
                assert info_index == -1
                info_index = idx
            elif arg_n in possible_wrapped_integer_inputs:
                possible_wrapped_integer_inputs_indices.append(idx)

        assert pos_index != -1, 'Could not find the "position" argument.'
        assert info_index != -1, 'Could not find the "info" argument.'
        assert len(possible_wrapped_integer_inputs_indices) == len(possible_wrapped_integer_inputs),\
            'Some of the argument names of the decorator could not be found.'
        possible_wrapped_integers = list(zip(possible_wrapped_integer_inputs_indices, possible_wrapped_integer_inputs))

        wrapped_int_type = None

        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            new_args = list(args)
            new_kwargs = dict(kwargs)
            _self = args[0]
            assert isinstance(_self, WrappedViperAST)
            nonlocal wrapped_int_type
            if wrapped_int_type is None:
                wrapped_int_type = helpers.wrapped_int_type(_self.viper_ast)

            had_wrapped_integers = wrap_output
            provided_arg_length = len(args)
            kwarg_names = set(kwargs.keys())

            pos = None
            info = None
            # Search for position and info arguments
            if pos_index < provided_arg_length:
                pos = args[pos_index]
            elif not kwarg_names.isdisjoint(pos_names):
                pos = next((kwargs[arg_name] for arg_name in pos_names if arg_name in kwargs))
            if info_index < provided_arg_length:
                info = args[info_index]
            elif not kwarg_names.isdisjoint(info_names):
                info = next((kwargs[arg_name] for arg_name in info_names if arg_name in kwargs))

            def unwrap(a: Expr) -> Expr:
                if hasattr(a, 'isSubtype') and a.isSubtype(wrapped_int_type):
                    nonlocal had_wrapped_integers
                    had_wrapped_integers = True
                    return helpers.w_unwrap(_self.viper_ast, a, pos, info)
                return a

            def wrap(a: Expr) -> Expr:
                if hasattr(a, 'isSubtype') and a.isSubtype(_self.viper_ast.Int):
                    return helpers.w_wrap(_self.viper_ast, a, pos, info)
                return a

            # Unwrap wrapped integers
            for index, arg_name in possible_wrapped_integers:
                arg: Optional[Union[Expr, Iterable]] = None
                if index < provided_arg_length:
                    arg = args[index]
                elif arg_name in kwarg_names:
                    arg = kwargs[arg_name]
                if arg is not None:
                    new_arg = [unwrap(a) for a in arg] if isinstance(arg, Iterable) else unwrap(arg)
                    if index < provided_arg_length:
                        new_args[index] = new_arg
                    else:  # There are only two ways to get "arg" and the first one was not it.
                        new_kwargs[arg_name] = new_arg

            # Call ast function
            value = func(*new_args, **new_kwargs)

            # Wrap output if one or more inputs were wrapped
            if had_wrapped_integers:
                if store_unwrap_info:
                    _self.unwrapped_some_expressions = True
                else:
                    value = wrap(value)
            return value
        return _wrapper
    return _decorator


class WrappedViperAST(ViperAST):

    def __init__(self, viper_ast: ViperAST):
        super().__init__(viper_ast.jvm)
        self.viper_ast = viper_ast
        self.unwrapped_some_expressions = False

    @wrapped_integer_decorator("args")
    def PredicateAccess(self, args, pred_name, position=None, info=None):
        return super().PredicateAccess(args, pred_name, position, info)

    @wrapped_integer_decorator("args")
    def DomainFuncApp(self, func_name, args, type_passed, position, info, domain_name, type_var_map=None):
        if type_var_map is None:
            type_var_map = {}
        return super().DomainFuncApp(func_name, args, type_passed, position, info, domain_name, type_var_map)

    @wrapped_integer_decorator("expr")
    def Minus(self, expr, position=None, info=None):
        return super().Minus(expr, position, info)

    @wrapped_integer_decorator("then", "els")
    def CondExp(self, cond, then, els, position=None, info=None):
        return super().CondExp(cond, then, els, position, info)

    @wrapped_integer_decorator("left", "right")
    def EqCmp(self, left, right, position=None, info=None):
        return super().EqCmp(left, right, position, info)

    @wrapped_integer_decorator("left", "right")
    def NeCmp(self, left, right, position=None, info=None):
        return super().NeCmp(left, right, position, info)

    @wrapped_integer_decorator("left", "right")
    def GtCmp(self, left, right, position=None, info=None):
        return super().GtCmp(left, right, position, info)

    @wrapped_integer_decorator("left", "right")
    def GeCmp(self, left, right, position=None, info=None):
        return super().GeCmp(left, right, position, info)

    @wrapped_integer_decorator("left", "right")
    def LtCmp(self, left, right, position=None, info=None):
        return super().LtCmp(left, right, position, info)

    @wrapped_integer_decorator("left", "right")
    def LeCmp(self, left, right, position=None, info=None):
        return super().LeCmp(left, right, position, info)

    @wrapped_integer_decorator("args", wrap_output=True)
    def FuncApp(self, name, args, position=None, info=None, type=None):
        return super().FuncApp(name, args, position, info, type)

    @wrapped_integer_decorator("elems")
    def ExplicitSeq(self, elems, position=None, info=None):
        return super().ExplicitSeq(elems, position, info)

    @wrapped_integer_decorator("elems")
    def ExplicitSet(self, elems, position=None, info=None):
        return super().ExplicitSet(elems, position, info)

    @wrapped_integer_decorator("elems")
    def ExplicitMultiset(self, elems, position=None, info=None):
        return super().ExplicitMultiset(elems, position, info)

    @wrapped_integer_decorator("right")
    def SeqAppend(self, left, right, position=None, info=None):
        return super().SeqAppend(left, right, position, info)

    @wrapped_integer_decorator("elem")
    def SeqContains(self, elem, s, position=None, info=None):
        return super().SeqContains(elem, s, position, info)

    @wrapped_integer_decorator("ind")
    def SeqIndex(self, s, ind, position=None, info=None):
        return super().SeqIndex(s, ind, position, info)

    @wrapped_integer_decorator("end")
    def SeqTake(self, s, end, position=None, info=None):
        return super().SeqTake(s, end, position, info)

    @wrapped_integer_decorator("end")
    def SeqDrop(self, s, end, position=None, info=None):
        return super().SeqDrop(s, end, position, info)

    @wrapped_integer_decorator("ind", "elem")
    def SeqUpdate(self, s, ind, elem, position=None, info=None):
        return super().SeqUpdate(s, ind, elem, position, info)

    @wrapped_integer_decorator("left", "right")
    def Add(self, left, right, position=None, info=None):
        return super().Add(left, right, position, info)

    @wrapped_integer_decorator("left", "right")
    def Sub(self, left, right, position=None, info=None):
        return super().Sub(left, right, position, info)

    @wrapped_integer_decorator("left", "right")
    def Mul(self, left, right, position=None, info=None):
        return super().Mul(left, right, position, info)

    @wrapped_integer_decorator("left", "right")
    def Div(self, left, right, position=None, info=None):
        return super().Div(left, right, position, info)

    @wrapped_integer_decorator("left", "right")
    def Mod(self, left, right, position=None, info=None):
        return super().Mod(left, right, position, info)
