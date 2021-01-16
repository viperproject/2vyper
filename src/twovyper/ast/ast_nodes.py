"""
Copyright (c) 2021 ETH Zurich
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

        self.is_ghost_code = False

    @property
    def children(self):
        return self._children


class AllowedInGhostCode:
    pass


class Stmt(Node):
    pass


class Expr(Node, AllowedInGhostCode):

    def __init__(self):
        super().__init__()
        self.type = None


class Operator(AllowedInGhostCode):
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
        super().__init__()
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

    def __init__(self, value: Expr, op: ContainmentOperator, list_expr: Expr):
        super().__init__()
        self.value = value
        self.op = op
        self.list = list_expr


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


class Set(Expr):

    _children = ['elements']

    def __init__(self, elements: ListT[Expr]):
        super().__init__()
        self.elements = elements


class Keyword(Node, AllowedInGhostCode):

    _children = ['value']

    def __init__(self, name: str, value: Expr):
        super().__init__()
        self.name = name
        self.value = value


class FunctionCall(Expr):

    _children = ['args', 'keywords', 'resource']

    def __init__(self, name: str, args: ListT[Expr], keywords: ListT[Keyword], resource: OptionalT[Expr] = None):
        super().__init__()
        self.name = name
        self.args = args
        self.keywords = keywords
        self.resource = resource
        self.underlying_resource = None


class ReceiverCall(Expr):

    _children = ['receiver', 'args', 'keywords']

    def __init__(self, name: str, receiver: Expr, args: ListT[Expr], keywords: ListT[Keyword]):
        super().__init__()
        self.name = name
        self.receiver = receiver
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


class Exchange(Expr):

    _children = ['left', 'right']

    def __init__(self, left: Expr, right: Expr):
        super().__init__()
        self.left = left
        self.right = right


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

    def __init__(self, id_str: str):
        super().__init__()
        self.id = id_str


class Dict(Expr):

    _children = ['keys', 'values']

    def __init__(self, keys: ListT[Name], values: ListT[Expr]):
        super().__init__()
        self.keys = keys
        self.values = values


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


class EventDef(Node):
    """
    Struct like event declaration
    """

    _children = ['body']

    def __init__(self, name: str, body: ListT[Stmt]):
        super().__init__()
        self.name = name
        self.body = body


class Arg(Node, AllowedInGhostCode):

    _children = ['annotation', 'default']

    def __init__(self, name: str, annotation: Expr, default: OptionalT[Expr]):
        super().__init__()
        self.name = name
        self.annotation = annotation
        self.default = default


class Decorator(Node, AllowedInGhostCode):

    _children = ['args']

    def __init__(self, name: str, args: ListT[Expr]):
        super().__init__()
        self.name = name
        self.args = args


class FunctionDef(Stmt, AllowedInGhostCode):

    _children = ['args', 'body', 'decorators', 'returns']

    def __init__(self, name: str, args: ListT[Arg], body: ListT[Stmt],
                 decorators: ListT[Decorator], returns: OptionalT[Expr]):
        super().__init__()
        self.name = name
        self.args = args
        self.body = body
        self.decorators = decorators
        self.returns = returns
        self.is_lemma = False


class FunctionStub(Stmt, AllowedInGhostCode):

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

    def __init__(self, target: Name, annotation: Expr, value: Expr):
        super().__init__()
        self.target = target
        self.annotation = annotation
        self.value = value


class For(Stmt):

    _children = ['target', 'iter', 'body']

    def __init__(self, target: Name, iter_expr: Expr, body: ListT[Stmt]):
        super().__init__()
        self.target = target
        self.iter = iter_expr
        self.body = body


class If(Stmt, AllowedInGhostCode):

    _children = ['test', 'body', 'orelse']

    def __init__(self, test: Expr, body: ListT[Stmt], orelse: ListT[Stmt]):
        super().__init__()
        self.test = test
        self.body = body
        self.orelse = orelse


class Log(Stmt, AllowedInGhostCode):

    _children = ['body']

    def __init__(self, body: Expr):
        super().__init__()
        self.body = body


class Ghost(Stmt, AllowedInGhostCode):

    _children = ['body']

    def __init__(self, body: ListT[Stmt]):
        super().__init__()
        self.body = body


class Raise(Stmt, AllowedInGhostCode):

    _children = ['msg']

    def __init__(self, msg: Expr):
        super().__init__()
        self.msg = msg


class Assert(Stmt, AllowedInGhostCode):

    _children = ['test', 'msg']

    def __init__(self, test: Expr, msg: OptionalT[Expr]):
        super().__init__()
        self.test = test
        self.msg = msg
        self.is_lemma = False


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


class ExprStmt(Stmt, AllowedInGhostCode):

    _children = ['value']

    def __init__(self, value: Expr):
        super().__init__()
        self.value = value


class Pass(Stmt, AllowedInGhostCode):
    pass


class Break(Stmt):
    pass


class Continue(Stmt):
    pass


def compare_nodes(first_node: Node, second_node: Node) -> bool:
    """
    Similar as vyper/ast/nodes.py:compare_nodes
    """
    if not isinstance(first_node, type(second_node)):
        return False

    for field_name in (i for i in first_node.children):
        left_value = getattr(first_node, field_name, None)
        right_value = getattr(second_node, field_name, None)

        # compare types instead of isinstance() in case one node class inherits the other
        if type(left_value) is not type(right_value):
            return False

        if isinstance(left_value, list):
            if next((i for i in zip(left_value, right_value) if not compare_nodes(*i)), None):
                return False
        elif isinstance(left_value, Node):
            if not compare_nodes(left_value, right_value):
                return False
        elif left_value != right_value:
            return False

    return True
