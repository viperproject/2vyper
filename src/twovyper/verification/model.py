"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import logging
from collections import OrderedDict
from typing import Any, Callable, Dict, Optional, Tuple

from twovyper.utils import seq_to_list
from twovyper.ast import types
from twovyper.ast.types import StructType, DecimalType, ArrayType, MapType, PrimitiveType
from twovyper.ast.arithmetic import Decimal
from twovyper.viper.typedefs import AbstractVerificationError


ModelTransformation = Callable[[str, Any], Optional[Tuple[str, str]]]


class Model:

    def __init__(self, error: AbstractVerificationError, jvm, transform: Optional[ModelTransformation]):
        ce = error.counterexample().get()
        scala_model = ce.model()
        model = OrderedDict()
        for entry in ScalaIterableWrapper(scala_model.entries()):
            self.extract_model_entry(entry, jvm, model)
        self._model = model
        self._store = ce.internalStore()
        self._names = transform and transform[0]
        self._types = transform and transform[1]
        self._jvm = jvm
        self.values()

    def extract_model_entry(self, entry, jvm, target):
        name = str(entry._1())
        value = entry._2()
        if isinstance(value, jvm.viper.silver.verifier.SingleEntry):
            target[name] = str(value.value())
        else:
            entry_val = OrderedDict()
            for option in ScalaIterableWrapper(value.options()):
                option_value = option._2()
                option_key = ()
                for option_key_entry in ScalaIterableWrapper(option._1()):
                    option_key += (str(option_key_entry),)
                entry_val[option_key] = str(option_value)
            entry_val['else'] = str(value.els())
            target[name] = entry_val

    def values(self) -> Dict[str, str]:
        res = {}
        if self._model and self._store and self._names:
            store_map = self._store.values()
            keys = seq_to_list(store_map.keys())
            for name_entry in keys:
                name = str(name_entry)
                term = store_map.get(name_entry).get()
                try:
                    value = evaluate_term(self._jvm, term, self._model)
                except NoFittingValueException:
                    continue

                transformation = self.transform_variable(name, value, term.sort())
                if transformation:
                    name, value = transformation
                    res[name] = value

        return res

    def transform_variable(self, name, value, sort):
        if name in self._names and name in self._types:
            vy_name = self._names[name]
            vy_type = self._types[name]
            value = str(value)
            return vy_name, self.transform_value(value, vy_type, sort)
        return None

    def parse_int(self, val):
        if val.startswith('(-') and val.endswith(')'):
            return - int(val[2:-1])
        return int(val)

    def transform_value(self, value, vy_type, sort):
        if isinstance(sort, self._jvm.viper.silicon.state.terms.sorts.UserSort) and str(sort.id()) == '$Int':
            value = get_func_value(self._model, '$unwrap<Int>', (value,))

        if isinstance(vy_type, PrimitiveType) and vy_type.name == 'bool':
            return value.capitalize()
        if isinstance(vy_type, DecimalType):
            value = self.parse_int(value)
            return str(Decimal[vy_type.number_of_digits](scaled_value=value))
        elif vy_type == types.VYPER_ADDRESS:
            value = self.parse_int(value)
            return f'{value:#0{40}x}'
        elif isinstance(vy_type, PrimitiveType):
            # assume int
            value = self.parse_int(value)
            return str(value)
        elif isinstance(vy_type, ArrayType):
            res = OrderedDict()
            length = get_func_value(self._model, SEQ_LENGTH, (value,))
            parsed_length = self.parse_int(length)
            if parsed_length > 0:
                indices, els_index = get_func_values(self._model, SEQ_INDEX, (value,))
                for ((index,), value) in indices:
                    converted_value = self.transform_value(value, vy_type.element_type, sort.elementsSort)
                    res[index] = converted_value
                if els_index is not None:
                    converted_value = self.transform_value(els_index, vy_type.element_type, sort.elementsSort)
                    res['_'] = converted_value
            return "[ {} ]: {}".format(', '.join(['{} -> {}'.format(k, v) for k, v in res.items()]), parsed_length)
        elif isinstance(vy_type, MapType):
            res = {}
            fname = '$map_get<{}>'.format(self.translate_type_name(vy_type.value_type))
            keys, els_val = get_func_values(self._model, fname, (value,))
            for ((key,), val) in keys:
                converted_key = self.transform_value(key, vy_type.key_type, self.translate_type_sort(vy_type.key_type))
                converted_value = self.transform_value(val, vy_type.value_type, self.translate_type_sort(vy_type.value_type))
                res[converted_key] = converted_value
            if els_val is not None:
                converted_value = self.transform_value(els_val, vy_type.value_type,
                                                       self.translate_type_sort(vy_type.value_type))
                res['_'] = converted_value
            return "{{ {} }}".format(', '.join(['{} -> {}'.format(k, v) for k, v in res.items()]))
        else:
            return value

    def translate_type_name(self, vy_type):
        if isinstance(vy_type, MapType):
            return '$Map<{}~_{}>'.format(self.translate_type_name(vy_type.key_type), self.translate_type_name(vy_type.value_type))
        if isinstance(vy_type, PrimitiveType) and vy_type.name == 'bool':
            return 'Bool'
        if isinstance(vy_type, PrimitiveType):
            return 'Int'
        if isinstance(vy_type, StructType):
            return '$Struct'
        raise Exception(vy_type)

    def translate_type_sort(self, vy_type):
        terms = self._jvm.viper.silicon.state.terms

        Identifier = self._jvm.viper.silicon.state.SimpleIdentifier

        def get_sort_object(name):
            return getattr(terms, 'sorts$' + name + '$')

        def get_sort_class(name):
            return getattr(terms, 'sorts$' + name)

        if isinstance(vy_type, MapType):
            name = '$Map<{}~_>'.format(self.translate_type_name(vy_type.key_type), self.translate_type_name(vy_type.value_type))
            return get_sort_class('UserSort')(Identifier(name))
        if isinstance(vy_type, PrimitiveType) and vy_type.name == 'bool':
            return get_sort_object('Bool')
        if isinstance(vy_type, PrimitiveType):
            return get_sort_object('Int')
        if isinstance(vy_type, StructType):
            return get_sort_class('UserSort')(Identifier('$Struct'))
        raise Exception(vy_type)

    def __str__(self):
        return "\n".join(f"   {name} = {value}" for name, value in sorted(self.values().items()))



SNAP_TO = '$SortWrappers.'
SEQ_LENGTH = 'Seq_length'
SEQ_INDEX = 'Seq_index'

UNIT = '$Snap.unit'


class ScalaIteratorWrapper:
    def __init__(self, iterator):
        self.iterator = iterator

    def __next__(self):
        if self.iterator.hasNext():
            return self.iterator.next()
        else:
            raise StopIteration


class ScalaIterableWrapper:
    def __init__(self, iterable):
        self.iterable = iterable

    def __iter__(self):
        return ScalaIteratorWrapper(self.iterable.toIterator())


class NoFittingValueException(Exception):
    pass


def get_func_value(model, name, args):
    args = tuple([' '.join(a.split()) for a in args])
    entry = model[name]
    if args == () and isinstance(entry, str):
        return entry
    res = entry.get(args)
    if res is not None:
        return res
    return model[name].get('else')


def get_func_values(model, name, args):
    args = tuple([' '.join(a.split()) for a in args])
    options = [(k[len(args):], v) for k, v in model[name].items() if k != 'else' and k[:len(args)] == args]
    els= model[name].get('else')
    return options, els


def get_parts(jvm, val):
    parser = getattr(getattr(jvm.viper.silver.verifier, 'ModelParser$'), 'MODULE$')
    res = []
    for part in ScalaIterableWrapper(parser.getApplication(val)):
        res.append(part)
    return res

def translate_sort(jvm, s):
    terms = jvm.viper.silicon.state.terms
    def get_sort_object(name):
        return getattr(terms, 'sorts$' + name + '$')
    def get_sort_class(name):
        return getattr(terms, 'sorts$' + name)

    if isinstance(s, get_sort_class('Set')):
        return 'Set<{}>'.format(translate_sort(jvm, s.elementsSort()))
    if isinstance(s, terms.UserSort):
        return '{}<{}>'.format(s.id(), translate_sort(jvm, s.elementsSort()))
    elif isinstance(s, get_sort_object('Ref')):
        return '$Ref'
    elif isinstance(s, get_sort_object('Snap')):
        return '$Snap'
    elif isinstance(s, get_sort_object('Perm')):
        return '$Perm'
    elif isinstance(s, get_sort_class('Seq')):
        return 'Seq<{}>'.format(translate_sort(jvm, s.elementsSort()))
    else:
        return str(s)


def evaluate_term(jvm, term, model):
    if isinstance(term, getattr(jvm.viper.silicon.state.terms, 'Unit$')):
        return '$Snap.unit'
    if isinstance(term, jvm.viper.silicon.state.terms.IntLiteral):
        return str(term)
    if isinstance(term, jvm.viper.silicon.state.terms.BooleanLiteral):
        return str(term)
    if isinstance(term, jvm.viper.silicon.state.terms.Null):
        return model['$Ref.null']
    if isinstance(term, jvm.viper.silicon.state.terms.Var):
        key = str(term)
        if key not in model:
            raise NoFittingValueException
        return model[key]
    elif isinstance(term, jvm.viper.silicon.state.terms.App):
        fname = str(term.applicable().id()) + '%limited'
        if fname not in model:
            fname = str(term.applicable().id())
            if fname not in model:
                fname = fname.replace('[', '<').replace(']', '>')
        args = []
        for arg in ScalaIterableWrapper(term.args()):
            args.append(evaluate_term(jvm, arg, model))
        res = get_func_value(model, fname, tuple(args))
        return res
    if isinstance(term, jvm.viper.silicon.state.terms.Combine):
        p0_val = evaluate_term(jvm, term.p0(), model)
        p1_val = evaluate_term(jvm, term.p1(), model)
        return '($Snap.combine ' + p0_val + ' ' + p1_val + ')'
    if isinstance(term, jvm.viper.silicon.state.terms.First):
        sub = evaluate_term(jvm, term.p(), model)
        if sub.startswith('($Snap.combine '):
            return get_parts(jvm, sub)[1]
    elif isinstance(term, jvm.viper.silicon.state.terms.Second):
        sub = evaluate_term(jvm, term.p(), model)
        if sub.startswith('($Snap.combine '):
            return get_parts(jvm, sub)[2]
    elif isinstance(term, jvm.viper.silicon.state.terms.SortWrapper):
        sub = evaluate_term(jvm, term.t(), model)
        from_sort_name = translate_sort(jvm, term.t().sort())
        to_sort_name = translate_sort(jvm, term.to())
        return get_func_value(model, SNAP_TO + from_sort_name + 'To' + to_sort_name, (sub,))
    elif isinstance(term, jvm.viper.silicon.state.terms.PredicateLookup):
        lookup_func_name = '$PSF.lookup_' + term.predname()
        toSnapTree = getattr(jvm.viper.silicon.state.terms, 'toSnapTree$')
        obj = getattr(toSnapTree, 'MODULE$')
        snap = obj.apply(term.args())
        psf_value = evaluate_term(jvm, term.psf(), model)
        snap_value = evaluate_term(jvm, snap, model)
        return get_func_value(model, lookup_func_name, (psf_value, snap_value))
    raise Exception(str(term))
