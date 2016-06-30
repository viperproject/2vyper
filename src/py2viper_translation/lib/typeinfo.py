import logging
import mypy.build
import mypy.fastparse
import sys

from functools import wraps
from mypy.build import BuildSource
from py2viper_translation.lib import config
from py2viper_translation.lib.constants import LITERALS
from py2viper_translation.lib.util import InvalidProgramException
from typing import List, Optional


logger = logging.getLogger('py2viper_translation.lib.typeinfo')


def col(node) -> Optional[int]:
    """
    Returns the column in a mypy mypy AST node, if any.
    """
    if hasattr(node, 'column'):
        return node.column
    return None


def with_column(f):
    @wraps(f)
    def wrapper(self, ast):
        node = f(self, ast)
        if hasattr(ast, 'col_offset'):
            node.column = ast.col_offset
        return node
    return wrapper


ASTConverter = mypy.fastparse.ASTConverter
for name in dir(ASTConverter):
    m = getattr(ASTConverter, name)
    if callable(m) and name.startswith('visit_'):
        setattr(ASTConverter, name, with_column(m))


class TypeException(Exception):
    def __init__(self, messages):
        self.messages = messages


class TypeVisitor(mypy.traverser.TraverserVisitor):
    def __init__(self, type_map, path, ignored_lines):
        self.prefix = []
        self.all_types = {}
        self.alt_types = {}
        self.type_map = type_map
        self.path = path
        self.ignored_lines = ignored_lines

    def _is_result_call(self, node: mypy.nodes.Node) -> bool:
        if isinstance(node, mypy.nodes.CallExpr):
            if node.callee.name == 'Result':
                return True
        return False

    def visit_member_expr(self, node: mypy.nodes.MemberExpr):
        rectype = self.type_of(node.expr)
        if (not self._is_result_call(node.expr) and
                not isinstance(rectype, mypy.types.CallableType)):
            self.set_type([rectype.type.name(), node.name], self.type_of(node),
                          node.line, col(node))
        super().visit_member_expr(node)

    def visit_try_stmt(self, node: mypy.nodes.TryStmt):
        for var in node.vars:
            if var is not None:
                self.set_type(self.prefix + [var.name], self.type_of(var),
                              var.line, col(var))
        for block in node.handlers:
            block.accept(self)

    def visit_name_expr(self, node: mypy.nodes.NameExpr):
        if not node.name in LITERALS:
            name_type = self.type_of(node)
            if not isinstance(name_type, mypy.types.CallableType):
                self.set_type(self.prefix + [node.name], name_type,
                              node.line, col(node))

    def visit_func_def(self, node: mypy.nodes.FuncDef):
        oldprefix = self.prefix
        self.prefix = self.prefix + [node.name()]
        functype = self.type_of(node)
        self.set_type(self.prefix, functype, node.line, col(node))
        for arg in node.arguments:
            self.set_type(self.prefix + [arg.variable.name()],
                          arg.variable.type, arg.line, col(arg))
        super().visit_func_def(node)
        self.prefix = oldprefix

    def visit_func_expr(self, node: mypy.nodes.FuncExpr):
        oldprefix = self.prefix
        prefix_string = 'lambda' + str(node.line)
        if col(node):
            prefix_string += '_' + str(col(node))
        self.prefix = self.prefix + [prefix_string]
        for arg in node.arguments:
            self.set_type(self.prefix + [arg.variable.name()],
                          arg.variable.type, arg.line, col(arg))
        node.body.accept(self)
        self.prefix = oldprefix

    def visit_class_def(self, node: mypy.nodes.ClassDef):
        oldprefix = self.prefix
        self.prefix = self.prefix + [node.name]
        super().visit_class_def(node)
        self.prefix = oldprefix

    def set_type(self, fqn, type, line, col):
        if isinstance(type, mypy.types.CallableType):
            type = type.ret_type
        if not type or isinstance(type, mypy.types.AnyType):
            if line in self.ignored_lines:
                return
            else:
                error = ' error: Encountered Any type. Type annotation missing?'
                msg = ':'.join([self.path, str(line), error])
                raise TypeException([msg])
        key = tuple(fqn)
        if key in self.all_types:
            if not self.type_equals(self.all_types[key], type):
                # type change after isinstance
                if key not in self.alt_types:
                    self.alt_types[key] = {}
                self.alt_types[key][(line, col)] = type
                return
        self.all_types[key] = type

    def type_equals(self, t1, t2):
        if str(t1) == str(t2):
            return True
        if (isinstance(t1, mypy.types.FunctionLike) and
                isinstance(t2, mypy.types.FunctionLike)):
            if self.type_equals(t1.ret_type, t2.ret_type):
                all_eq = True
                for arg1, arg2 in zip(t1.arg_types, t2.arg_types):
                    all_eq = all_eq and self.type_equals(arg1, arg2)
                return all_eq
        return t1 == t2

    def visit_call_expr(self, node: mypy.nodes.CallExpr):
        for a in node.args:
            a.accept(self)
        node.callee.accept(self)

    def type_of(self, node):
        if isinstance(node, mypy.nodes.FuncDef):
            if node.type:
                return node.type
        elif isinstance(node, mypy.nodes.CallExpr):
            if node.callee.name == 'Result':
                type = self.all_types[tuple(self.prefix)]
                return type
        if node in self.type_map:
            result = self.type_map[node]
            return result
        else:
            msg = self.path + ':' + str(node.get_line()) + ': error: '
            if isinstance(node, mypy.nodes.FuncDef):
                msg += 'Encountered Any type. Type annotation missing?'
            else:
                msg += 'dead.code'
            raise TypeException([msg])

    def visit_comparison_expr(self, o: mypy.nodes.ComparisonExpr):
        # weird things seem to happen with is-comparisons, so we ignore those.
        if 'is' not in o.operators and 'is not' not in o.operators:
            super().visit_comparison_expr(o)


class TypeInfo:
    """
    Provides type information for all variables and functions in a given
    Python program.
    """

    def __init__(self):
        self.all_types = {}
        self.alt_types = {}

    def check(self, filename: str) -> bool:
        """
        Typechecks the given file and collects all type information needed for
        the translation to Viper
        """

        def report_errors(errors: List[str]) -> None:
            for error in errors:
                logger.info(error)
            raise TypeException(errors)

        try:
            res = mypy.build.build(
                [BuildSource(filename, None, None)],
                target=mypy.build.TYPE_CHECK,
                bin_dir=config.mypy_dir,
                flags=[mypy.build.FAST_PARSER]
                )
            if res.errors:
                report_errors(res.errors)
            visitor = TypeVisitor(res.types, filename,
                                  res.files['__main__'].ignored_lines)
            # for df in res.files['__main__'].defs:
            # print(df)
            res.files['__main__'].accept(visitor)
            self.all_types.update(visitor.all_types)
            self.alt_types.update(visitor.alt_types)
            return True
        except mypy.errors.CompileError as e:
            report_errors(e.messages)

    def get_type(self, prefix: List[str], name: str):
        """
        Looks up the inferred or annotated type for the given name in the given
        prefix
        """
        key = tuple(prefix + [name])
        result = self.all_types.get(key)
        alts = self.alt_types.get(key)
        if result is None:
            if not prefix:
                return None, None
            else:
                return self.get_type(prefix[:len(prefix) - 1], name)
        else:
            return result, alts

    def get_func_type(self, prefix: List[str]):
        """
        Looks up the type of the function which creates the given context
        """
        result = self.all_types.get(tuple(prefix))
        if result is None:
            if len(prefix) == 0:
                return None
            else:
                return self.get_func_type(prefix[:len(prefix) - 1])
        else:
            if isinstance(result, mypy.types.FunctionLike):
                result = result.ret_type
            return result

    def is_normal_type(self, type: mypy.types.Type) -> bool:
        return isinstance(type, mypy.nodes.TypeInfo)

    def is_instance_type(self, type: mypy.types.Type) -> bool:
        return isinstance(type, mypy.types.Instance)

    def is_tuple_type(self, type: mypy.types.Type) -> bool:
        return isinstance(type, mypy.types.TupleType)

    def is_void_type(self, type: mypy.types.Type) -> bool:
        return isinstance(type, mypy.types.Void)
