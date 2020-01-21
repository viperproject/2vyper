"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from enum import Enum
from typing import List as ListT, Optional as OptionalT


class Node:

    _children: ListT[str] = []

    def __init__(self):
        self.file = None
        self.lineno = None
        self.col_offset = None
        self.end_lineno = None
        self.end_col_offset = None


class Stmt(Node):
    pass


class Expr(Node):

    def __init__(self):
        super().__init__()
        self.type = None


class Operator:
    pass


class BoolOperator(Operator, Enum):
    AND = 'and'
    OR = 'or'
    IMPLIES = 'implies'


class BoolOp(Expr):

    _children = ['left', 'right']

    def __init__(self, left: Expr, op: BoolOperator, right: Expr):
        super().__init__()
        self.left = left
        self.op = op
        self.right = right


class Not(Expr):

    _children = ['operand']

    def __init__(self, operand: Expr):
        self.operand = operand


class ArithmeticOperator(Operator, Enum):
    ADD = '+'
    SUB = '-'
    MUL = '*'
    DIV = '/'
    MOD = '%'
    POW = '**'


class ArithmeticOp(Expr):

    _children = ['left', 'right']

    def __init__(self, left: Expr, op: ArithmeticOperator, right: Expr):
        super().__init__()
        self.left = left
        self.op = op
        self.right = right


class UnaryArithmeticOperator(Operator, Enum):
    ADD = '+'
    SUB = '-'


class UnaryArithmeticOp(Expr):

    _children = ['operand']

    def __init__(self, op: UnaryArithmeticOperator, operand: Expr):
        super().__init__()
        self.op = op
        self.operand = operand


class ComparisonOperator(Operator, Enum):
    LT = '<'
    LTE = '<='
    GTE = '>='
    GT = '>'


class Comparison(Expr):

    _children = ['left', 'right']

    def __init__(self, left: Expr, op: ComparisonOperator, right: Expr):
        super().__init__()
        self.left = left
        self.op = op
        self.right = right


class ContainmentOperator(Operator, Enum):
    IN = 'in'
    NOT_IN = 'not in'


class Containment(Expr):

    _children = ['value', 'list']

    def __init__(self, value: Expr, op: ContainmentOperator, list: Expr):
        super().__init__()
        self.value = value
        self.op = op
        self.list = list


class EqualityOperator(Operator, Enum):
    EQ = '=='
    NEQ = '!='


class Equality(Expr):

    _children = ['left', 'right']

    def __init__(self, left: Expr, op: EqualityOperator, right: Expr):
        super().__init__()
        self.left = left
        self.op = op
        self.right = right


class IfExpr(Expr):

    _children = ['test', 'body', 'orelse']

    def __init__(self, test: Expr, body: Expr, orelse: Expr):
        super().__init__()
        self.test = test
        self.body = body
        self.orelse = orelse


class Dict(Expr):

    _children = ['keys', 'values']

    def __init__(self, keys: ListT[Expr], values: ListT[Expr]):
        super().__init__()
        self.keys = keys
        self.values = values


class Set(Expr):

    _children = ['elements']

    def __init__(self, elements: ListT[Expr]):
        super().__init__()
        self.elements = elements


class Keyword(Node):

    _children = ['value']

    def __init__(self, name: str, value: Expr):
        super().__init__()
        self.name = name
        self.value = value


class Call(Expr):

    _children = ['func', 'args', 'keywords']

    def __init__(self, func: Expr, args: ListT[Expr], keywords: ListT[Keyword]):
        super().__init__()
        self.func = func
        self.args = args
        self.keywords = keywords


class Num(Expr):

    def __init__(self, n):
        super().__init__()
        self.n = n


class Str(Expr):

    def __init__(self, s: str):
        super().__init__()
        self.s = s


class Bytes(Expr):

    def __init__(self, s: bytes):
        super().__init__()
        self.s = s


class Bool(Expr):

    def __init__(self, value):
        super().__init__()
        self.value = value


class Ellipsis(Expr):
    pass


class Attribute(Expr):

    _children = ['value']

    def __init__(self, value: Expr, attr: str):
        super().__init__()
        self.value = value
        self.attr = attr


class Subscript(Expr):

    _children = ['value', 'index']

    def __init__(self, value: Expr, index: Expr):
        super().__init__()
        self.value = value
        self.index = index


class Name(Expr):

    def __init__(self, id: str):
        super().__init__()
        self.id = id


class List(Expr):

    _children = ['elements']

    def __init__(self, elements: ListT[Expr]):
        super().__init__()
        self.elements = elements


class Tuple(Expr):

    _children = ['elements']

    def __init__(self, elements: ListT[Expr]):
        super().__init__()
        self.elements = elements


class Module(Node):

    _children = ['stmts']

    def __init__(self, stmts: ListT[Stmt]):
        super().__init__()
        self.stmts = stmts


class StructDef(Node):

    _children = ['body']

    def __init__(self, name: str, body: ListT[Stmt]):
        super().__init__()
        self.name = name
        self.body = body


class ContractDef(Node):

    _children = ['body']

    def __init__(self, name: str, body: ListT[Stmt]):
        super().__init__()
        self.name = name
        self.body = body


class Arg(Node):

    _children = ['annotation', 'default']

    def __init__(self, name: str, annotation: Expr, default: OptionalT[Expr]):
        super().__init__()
        self.name = name
        self.annotation = annotation
        self.default = default


class Decorator(Node):

    _children = ['args']

    def __init__(self, name: str, args: ListT[Expr]):
        super().__init__()
        self.name = name
        self.args = args


class FunctionDef(Stmt):

    _children = ['args', 'body', 'decorators', 'returns']

    def __init__(self, name: str, args: ListT[Arg], body: ListT[Stmt], decorators: ListT[Decorator], returns: OptionalT[Expr]):
        super().__init__()
        self.name = name
        self.args = args
        self.body = body
        self.decorators = decorators
        self.returns = returns


class FunctionStub(Stmt):

    _children = ['args']

    def __init__(self, name: str, args: ListT[Arg], returns: OptionalT[Expr]):
        super().__init__()
        self.name = name
        self.args = args
        self.returns = returns


class Return(Stmt):

    _children = ['value']

    def __init__(self, value: OptionalT[Expr]):
        super().__init__()
        self.value = value


class Assign(Stmt):

    _children = ['target', 'value']

    def __init__(self, target: Expr, value: Expr):
        super().__init__()
        self.target = target
        self.value = value


class AugAssign(Stmt):

    _children = ['target', 'value']

    def __init__(self, target: Expr, op: ArithmeticOperator, value: Expr):
        super().__init__()
        self.target = target
        self.op = op
        self.value = value


class AnnAssign(Stmt):

    _children = ['target', 'annotation', 'value']

    def __init__(self, target: Expr, annotation: Expr, value: Expr):
        super().__init__()
        self.target = target
        self.annotation = annotation
        self.value = value


class For(Stmt):

    _children = ['target', 'iter', 'body']

    def __init__(self, target: Name, iter: Expr, body: ListT[Stmt]):
        super().__init__()
        self.target = target
        self.iter = iter
        self.body = body


class If(Stmt):

    _children = ['test', 'body', 'orelse']

    def __init__(self, test: Expr, body: ListT[Stmt], orelse: ListT[Stmt]):
        super().__init__()
        self.test = test
        self.body = body
        self.orelse = orelse


class Ghost(Stmt):

    _children = ['body']

    def __init__(self, body: ListT[Stmt]):
        super().__init__()
        self.body = body


class Raise(Stmt):

    _children = ['msg']

    def __init__(self, msg: Expr):
        super().__init__()
        self.msg = msg


class Assert(Stmt):

    _children = ['test', 'msg']

    def __init__(self, test: Expr, msg: Expr):
        super().__init__()
        self.test = test
        self.msg = msg


class Alias(Node):

    def __init__(self, name: str, asname: OptionalT[str]):
        super().__init__()
        self.name = name
        self.asname = asname


class Import(Stmt):

    _children = ['names']

    def __init__(self, names: ListT[Alias]):
        super().__init__()
        self.names = names


class ImportFrom(Stmt):

    _children = ['names']

    def __init__(self, module: OptionalT[str], names: ListT[Alias], level: int):
        super().__init__()
        self.module = module
        self.names = names
        self.level = level


class ExprStmt(Stmt):

    _children = ['value']

    def __init__(self, value: Expr):
        super().__init__()
        self.value = value


class Pass(Stmt):
    pass


class Break(Stmt):
    pass


class Continue(Stmt):
    pass
