"""Public interface to obligation translator."""


import ast

from typing import List, Tuple, Union

from py2viper_translation.lib.context import Context
from py2viper_translation.lib.jvmaccess import JVM
from py2viper_translation.lib.program_nodes import (
    PythonMethod,
)
from py2viper_translation.lib.typedefs import (
    Expr,
    Info,
    Field,
    Position,
    Predicate,
    Stmt,
    StmtsAndExpr,
    VarDecl,
)
from py2viper_translation.lib.typeinfo import TypeInfo
from py2viper_translation.lib.util import (
    get_func_name,
    InvalidProgramException,
    UnsupportedException,
)
from py2viper_translation.lib.viper_ast import ViperAST
from py2viper_translation.translators.abstract import TranslatorConfig
from py2viper_translation.translators.common import CommonTranslator
from py2viper_translation.translators.obligation.loop import (
    LoopObligationTranslator,
)
from py2viper_translation.translators.obligation.manager import (
    ObligationManager,
)
from py2viper_translation.translators.obligation.method import (
    MethodObligationTranslator,
)
from py2viper_translation.translators.obligation.visitors import (
    PythonMethodObligationInfo,
)


class ObligationTranslator(CommonTranslator):
    """Translator for obligations."""

    def __init__(self, config: TranslatorConfig, jvm: JVM, source_file: str,
                 type_info: TypeInfo, viper_ast: ViperAST) -> None:
        super().__init__(config, jvm, source_file, type_info, viper_ast)
        self._obligation_manager = ObligationManager()
        self._method_translator = MethodObligationTranslator(
            config, jvm, source_file, type_info, viper_ast)
        self._loop_translator = LoopObligationTranslator(
            config, jvm, source_file, type_info, viper_ast)

    def enter_loop_translation(
            self, node: Union[ast.While, ast.For], ctx: Context) -> None:
        """Update context with info needed to translate loop."""
        self._loop_translator.enter_loop_translation(node, ctx)

    def leave_loop_translation(self, ctx: Context) -> None:
        """Remove loop translation info from context."""
        self._loop_translator.leave_loop_translation(ctx)

    def create_while_node(
            self, ctx: Context, cond: Expr,
            invariants: List[Expr],
            local_vars: List[VarDecl],
            body: Stmt, node: Union[ast.While, ast.For]) -> List[Stmt]:
        """Construct a while loop AST node with obligation stuff."""
        return self._loop_translator.create_while_node(
            ctx, cond, invariants, local_vars, body, node)

    def translate_obligation_contractfunc_call(
            self, node: ast.Call, ctx: Context) -> StmtsAndExpr:
        """Translate a call to obligation contract function."""
        func_name = get_func_name(node)
        if func_name == 'MustTerminate':
            return self._translate_must_terminate(node, ctx)
        else:
            raise UnsupportedException(
                node, 'Unsupported contract function.')

    def _translate_must_terminate(
            self, node: ast.Call, ctx: Context) -> StmtsAndExpr:
        """Translate a call to ``MustTerminate``."""
        if ctx.obligation_context.is_translating_loop():
            return self._loop_translator.translate_must_terminate(node, ctx)
        elif ctx.obligation_context.is_translating_posts:
            raise InvalidProgramException(
                node, 'obligation.must_terminate.in_postcondition')
        else:
            return self._method_translator.translate_must_terminate(node, ctx)

    def get_obligation_preamble(
            self,
            ctx: Context) -> Tuple[List[Predicate], List[Field]]:
        """Construct obligation preamble.

        To track each obligation we use predicates which are defined in
        this preamble.
        """
        predicates = self._obligation_manager.create_predicates(self)
        return predicates, []

    def create_method_node(
            self, ctx: Context, name: str,
            args: List[VarDecl], returns: List[VarDecl],
            pres: List[Expr], posts: List[Expr],
            local_vars: List[VarDecl], body: List[Stmt],
            position: Position, info: Info,
            method: PythonMethod = None) -> List[Stmt]:
        """Construct method AST node with additional obligation stuff."""
        return self._method_translator.create_method_node(
            ctx, name, args, returns, pres, posts, local_vars, body,
            position, info, method)

    def create_method_call_node(
            self, ctx: Context, methodname: str, args: List[Expr],
            targets: List[Expr], position: Position, info: Info,
            target_method: PythonMethod = None,
            target_node: ast.Call = None) -> List[Stmt]:
        """Construct a method call AST node with obligation stuff."""
        return self._method_translator.create_method_call_node(
            ctx, methodname, args, targets, position, info,
            target_method, target_node)

    def create_obligation_info(self, method: PythonMethod) -> object:
        """Create obligation info for the method."""
        info = PythonMethodObligationInfo(
            self._obligation_manager, method, self.translator)
        info.traverse_preconditions()
        info.traverse_postconditions()
        return info
