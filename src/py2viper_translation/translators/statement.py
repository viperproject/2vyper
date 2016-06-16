import ast

from py2viper_translation.lib.constants import (
    DICT_TYPE,
    END_LABEL,
    LIST_TYPE,
    PRIMITIVES,
    SET_TYPE,
    TUPLE_TYPE,
)
from py2viper_translation.lib.program_nodes import PythonType, PythonVar
from py2viper_translation.lib.typedefs import (
    Expr,
    Stmt,
    StmtsAndExpr,
)
from py2viper_translation.lib.util import (
    flatten,
    get_func_name,
    get_surrounding_try_blocks,
    InvalidProgramException,
    UnsupportedException,
)
from py2viper_translation.translators.abstract import Context
from py2viper_translation.translators.common import CommonTranslator
from typing import List, Optional


class StatementTranslator(CommonTranslator):

    def translate_stmt(self, node: ast.AST, ctx: Context) -> List[Stmt]:
        """
        Generic visitor function for translating statements
        """
        method = 'translate_stmt_' + node.__class__.__name__
        visitor = getattr(self, method, self.translate_generic)
        return visitor(node, ctx)

    def translate_stmt_AugAssign(self, node: ast.AugAssign,
                                 ctx: Context) -> List[Stmt]:
        lhs_stmt, lhs = self.translate_expr(node.target, ctx)
        if lhs_stmt:
            raise InvalidProgramException(node, 'purity.violated')
        rhs_stmt, rhs = self.translate_expr(node.value, ctx)
        if isinstance(node.op, ast.Add):
            newval = self.viper.Add(lhs, rhs,
                                    self.to_position(node, ctx),
                                    self.no_info(ctx))
        elif isinstance(node.op, ast.Sub):
            newval = self.viper.Sub(lhs, rhs,
                                    self.to_position(node, ctx),
                                    self.no_info(ctx))
        elif isinstance(node.op, ast.Mult):
            newval = self.viper.Mul(lhs, rhs,
                                    self.to_position(node, ctx),
                                    self.no_info(ctx))
        else:
            raise UnsupportedException(node)
        position = self.to_position(node, ctx)
        if isinstance(node.target, ast.Name):
            assign = self.viper.LocalVarAssign(lhs, newval, position,
                                               self.no_info(ctx))
        elif isinstance(node.target, ast.Attribute):
            assign = self.viper.FieldAssign(lhs, newval, position,
                                            self.no_info(ctx))
        return rhs_stmt + [assign]

    def translate_stmt_Pass(self, node: ast.Pass, ctx: Context) -> List[Stmt]:
        return []

    def _create_for_loop_invariant(self, iter_var: PythonVar,
                                   target_var: PythonVar,
                                   err_var: PythonVar,
                                   iterable: Expr,
                                   iterable_type: PythonType,
                                   node: ast.AST,
                                   ctx: Context) -> List[Stmt]:
        np = self.no_position(ctx)
        ni = self.no_info(ctx)
        seq_ref = self.viper.SeqType(self.viper.Ref)
        set_ref = self.viper.SetType(self.viper.Ref)

        param = self.viper.LocalVarDecl('self', self.viper.Ref, np, ni)

        seq_func_name = iterable_type.name + '___sil_seq__'
        iter_seq = self.viper.FuncApp(seq_func_name, [iterable], np, ni,
                                      seq_ref, [param])
        invar_args = [iter_var.ref, iter_seq, err_var.ref, target_var.ref]
        invar_pred = self.viper.PredicateAccess(invar_args, 'for_invariant', np,
                                                ni)
        full_perm = self.viper.FullPerm(np, ni)

        invariant = []
        one = self.viper.IntLit(1, np, ni)
        zero = self.viper.IntLit(0, np, ni)
        twenty = self.viper.IntLit(20, np, ni)
        frac_perm_120 = self.viper.FractionalPerm(one, twenty, np, ni)
        if iterable_type.name in {DICT_TYPE, LIST_TYPE, SET_TYPE}:
            field_name = iterable_type.name + '_acc'
            field_type = seq_ref if iterable_type.name == LIST_TYPE else set_ref
            acc_field = self.viper.Field(field_name, field_type, np, ni)
            field_acc = self.viper.FieldAccess(iterable, acc_field, np, ni)
            field_pred = self.viper.FieldAccessPredicate(field_acc,
                                                         frac_perm_120, np, ni)
            invariant.append(field_pred)
        else:
            raise UnsupportedException(node)

        list_acc_field = self.viper.Field('list_acc', seq_ref, np, ni)
        iter_acc = self.viper.FieldAccess(iter_var.ref, list_acc_field, np, ni)
        iter_acc_pred = self.viper.FieldAccessPredicate(iter_acc, frac_perm_120,
                                                        np, ni)
        invariant.append(iter_acc_pred)

        iter_list_equal = self.viper.EqCmp(iter_acc, iter_seq, np, ni)
        invariant.append(iter_list_equal)

        index_field = self.viper.Field('__iter_index', self.viper.Int, np, ni)
        iter_index_acc = self.viper.FieldAccess(iter_var.ref, index_field, np,
                                                ni)
        iter_index_acc_pred = self.viper.FieldAccessPredicate(iter_index_acc,
                                                              full_perm, np, ni)
        invariant.append(iter_index_acc_pred)

        previous_field = self.viper.Field('__previous', self.viper.Ref, np, ni)
        iter_previous_acc = self.viper.FieldAccess(iter_var.ref, previous_field,
                                                   np, ni)
        iter_previous_acc_pred = self.viper.FieldAccessPredicate(
            iter_previous_acc, frac_perm_120, np, ni)
        invariant.append(iter_previous_acc_pred)

        previous_list_acc = self.viper.FieldAccess(iter_previous_acc,
                                                   list_acc_field, np, ni)
        previous_list_acc_pred = self.viper.FieldAccessPredicate(
            previous_list_acc, full_perm, np, ni)
        invariant.append(previous_list_acc_pred)

        index_minus_one = self.viper.Sub(iter_index_acc, one, np, ni)
        object_class = ctx.program.classes['object']
        list_class = ctx.program.classes['list']
        previous_len = self.get_function_call(list_class, '__len__',
                                              [iter_previous_acc],
                                              [object_class], None, ctx)
        previous_len_eq = self.viper.EqCmp(index_minus_one, previous_len, np,
                                           ni)
        invariant.append(previous_len_eq)

        no_error = self.viper.EqCmp(err_var.ref, self.viper.NullLit(np, ni),
                                    np, ni)
        some_error = self.viper.NeCmp(err_var.ref, self.viper.NullLit(np, ni),
                                      np, ni)

        index_nonneg = self.viper.GeCmp(iter_index_acc, zero, np, ni)
        iter_list_len = self.viper.SeqLength(iter_acc, np, ni)
        index_le_len = self.viper.LeCmp(iter_index_acc, iter_list_len, np, ni)
        index_bounds = self.viper.And(index_nonneg, index_le_len, np, ni)
        invariant.append(self.viper.Implies(no_error, index_bounds, np, ni))

        iter_current_index = self.viper.SeqIndex(iter_acc, index_minus_one, np,
                                                 ni)
        boxed_target = target_var.ref
        if target_var.type.name in PRIMITIVES:
            boxed_target = self.box_primitive(boxed_target, target_var.type,
                                              None, ctx)
            iter_current_index = self.unbox_primitive(iter_current_index,
                                                      target_var.type, None,
                                                      ctx)

        current_element_index = self.viper.EqCmp(target_var.ref,
                                                 iter_current_index, np, ni)
        current_element_contained = self.viper.SeqContains(boxed_target,
                                                           iter_acc, np, ni)
        invariant.append(self.viper.Implies(no_error, current_element_index, np,
                                            ni))
        invariant.append(self.viper.Implies(no_error, current_element_contained,
                                            np, ni))

        previous_elements = self.viper.SeqTake(iter_acc, index_minus_one, np,
                                               ni)
        iter_previous_contents = self.viper.EqCmp(previous_list_acc,
                                                  previous_elements, np, ni)
        invariant.append(self.viper.Implies(no_error, iter_previous_contents,
                                            np, ni))

        previous_is_all = self.viper.EqCmp(previous_list_acc, iter_acc, np, ni)
        invariant.append(self.viper.Implies(some_error, previous_is_all, np,
                                            ni))
        return invariant

    def translate_stmt_For(self, node: ast.For, ctx: Context) -> List[Stmt]:
        iterable_type = self.get_type(node.iter, ctx)
        iterable_stmt, iterable = self.translate_expr(node.iter, ctx)
        iter_class = ctx.program.classes['Iterator']
        iter_var = ctx.actual_function.create_variable('iter', iter_class,
                                                       self.translator)
        target_var = ctx.actual_function.get_variable(node.target.id)
        if target_var.type.name in PRIMITIVES:
            boxed_target_type = ctx.program.classes['__boxed_' +
                                                    target_var.type.name]
        else:
            boxed_target_type = target_var.type
        boxed_target_var = ctx.actual_function.create_variable('target',
                                                               boxed_target_type,
                                                               self.translator)
        node._iterator = iter_var
        args = [iterable]
        arg_types = [iterable_type]
        iter_assign = self.get_method_call(iterable_type, '__iter__', args,
                                           arg_types, [iter_var.ref], node, ctx)
        exc_class = ctx.program.classes['Exception']
        err_var = ctx.actual_function.create_variable('iter_err', exc_class,
                                                      self.translator)

        args = [iter_var.ref]
        arg_types = [iter_class]
        targets = [boxed_target_var.ref, err_var.ref]
        next_call = self.get_method_call(iter_class, '__next__', args,
                                         arg_types, targets, node, ctx)

        np = self.no_position(ctx)
        ni = self.no_info(ctx)
        if target_var.type.name in PRIMITIVES:
            unboxed_target = self.unbox_primitive(boxed_target_var.ref,
                                                  target_var.type, None, ctx)
        else:
            unboxed_target = boxed_target_var.ref
        target_assign = self.viper.LocalVarAssign(target_var.ref,
                                                  unboxed_target, np, ni)

        seq_ref = self.viper.SeqType(self.viper.Ref)
        set_ref = self.viper.SetType(self.viper.Ref)

        invariant = self._create_for_loop_invariant(iter_var, target_var,
                                                    err_var, iterable,
                                                    iterable_type, node, ctx)
        locals = []
        bodyindex = 0

        while self.is_invariant(node.body[bodyindex]):
            inv_node = node.body[bodyindex]
            user_inv = self.translate_contract(inv_node, ctx)
            invariant.append(user_inv)
            bodyindex += 1
        body = []
        body += flatten(
            [self.translate_stmt(stmt, ctx) for stmt in node.body[bodyindex:]])
        body.append(next_call)
        body.append(target_assign)
        body_block = self.translate_block(body,
                                          self.to_position(node, ctx),
                                          self.no_info(ctx))
        cond = self.viper.EqCmp(err_var.ref,
                                self.viper.NullLit(self.no_position(ctx),
                                                   self.no_info(ctx)),
                                self.to_position(node, ctx),
                                self.no_info(ctx))
        loop = self.viper.While(cond, invariant, locals, body_block,
                                self.to_position(node, ctx), self.no_info(ctx))
        iter_del = self.get_method_call(iter_class, '__del__', args, arg_types,
                                        [], node, ctx)
        return [iter_assign, next_call, target_assign, loop, iter_del]

    def translate_stmt_Try(self, node: ast.Try, ctx: Context) -> List[Stmt]:
        try_block = None
        for block in ctx.actual_function.try_blocks:
            if block.node is node:
                try_block = block
                break
        assert try_block
        code_var = try_block.get_finally_var(self.translator)
        if code_var.sil_name in ctx.var_aliases:
            code_var = ctx.var_aliases[code_var.sil_name]
        code_var = code_var.ref
        zero = self.viper.IntLit(0, self.no_position(ctx), self.no_info(ctx))
        assign = self.viper.LocalVarAssign(code_var, zero,
                                           self.no_position(ctx),
                                           self.no_info(ctx))
        body = [assign]
        body += flatten([self.translate_stmt(stmt, ctx) for stmt in node.body])
        if try_block.else_block:
            else_label = ctx.get_label_name(try_block.else_block.name)
            goto = self.viper.Goto(else_label,
                                   self.to_position(node, ctx),
                                   self.no_info(ctx))
            body += [goto]
        elif try_block.finally_block:
            finally_name = ctx.get_label_name(try_block.finally_name)
            goto = self.viper.Goto(finally_name,
                                   self.to_position(node, ctx),
                                   self.no_info(ctx))
            body += [goto]
        label_name = ctx.get_label_name(try_block.post_name)
        end_label = self.viper.Label(label_name,
                                     self.to_position(node, ctx),
                                     self.no_info(ctx))
        return body + [end_label]

    def translate_stmt_Raise(self, node: ast.Raise, ctx: Context) -> List[Stmt]:
        var = self.get_error_var(node, ctx)
        stmt, exception = self.translate_expr(node.exc, ctx)
        assignment = self.viper.LocalVarAssign(var, exception,
                                               self.to_position(node, ctx),
                                               self.no_info(ctx))
        catchers = self.create_exception_catchers(var,
            ctx.actual_function.try_blocks, node, ctx)
        return stmt + [assignment] + catchers

    def translate_stmt_Call(self, node: ast.Call, ctx: Context) -> List[Stmt]:
        stmt, expr = self.translate_Call(node, ctx)
        if expr:
            type = self.get_type(node, ctx)
            var = ctx.current_function.create_variable('expr', type,
                                                       self.translator)
            assign = self.viper.LocalVarAssign(var.ref, expr,
                                               self.to_position(node, ctx),
                                               self.no_info(ctx))
            stmt.append(assign)
        return stmt

    def translate_stmt_Expr(self, node: ast.Expr, ctx: Context) -> List[Stmt]:
        if isinstance(node.value, ast.Call):
            return self.translate_stmt(node.value, ctx)
        else:
            raise UnsupportedException(node)

    def translate_stmt_If(self, node: ast.If, ctx: Context) -> List[Stmt]:
        cond_stmt, cond = self.translate_to_bool(node.test, ctx)
        then_body = flatten([self.translate_stmt(stmt, ctx)
                             for stmt in node.body])
        then_block = self.translate_block(then_body,
                                          self.to_position(node, ctx),
                                          self.no_info(ctx))
        else_body = flatten([self.translate_stmt(stmt, ctx)
                             for stmt in node.orelse])
        else_block = self.translate_block(
            else_body,
            self.to_position(node, ctx), self.no_info(ctx))
        position = self.to_position(node, ctx)
        return cond_stmt + [self.viper.If(cond, then_block, else_block,
                                          position, self.no_info(ctx))]

    def assign_to(self, lhs: ast.AST, rhs: Expr, rhs_index: Optional[int],
                  rhs_type: PythonType, node: ast.AST,
                  ctx: Context) -> List[Stmt]:
        if rhs_index is not None:
            index_lit = self.viper.IntLit(rhs_index, self.no_position(ctx),
                                          self.no_info(ctx))
            args = [rhs, index_lit]
            arg_types = [rhs_type, None]
            rhs = self.get_function_call(rhs_type, '__getitem__', args,
                                         arg_types, node, ctx)
            rhs_index_type = rhs_type.type_args[rhs_index]
            if rhs_index_type.name in PRIMITIVES:
                rhs = self.unbox_primitive(rhs, rhs_index_type, node, ctx)
        if isinstance(lhs, ast.Subscript):
            if not isinstance(node.targets[0].slice, ast.Index):
                raise UnsupportedException(node)
            target_cls = self.get_type(lhs.value, ctx)
            lhs_stmt, target = self.translate_expr(lhs.value, ctx)
            ind_stmt, index = self.translate_expr(lhs.slice.value, ctx)
            index_type = self.get_type(lhs.slice.value, ctx)

            args = [target, index, rhs]
            arg_types = [None, index_type, rhs_type]
            call = self.get_method_call(target_cls, '__setitem__', args,
                                        arg_types, [], node, ctx)
            return lhs_stmt + ind_stmt + [call]
        target = lhs
        lhs_stmt, var = self.translate_expr(target, ctx)
        if isinstance(target, ast.Name):
            assignment = self.viper.LocalVarAssign
        else:
            assignment = self.viper.FieldAssign
        assign = assignment(var,
                            rhs, self.to_position(node, ctx),
                            self.no_info(ctx))
        return lhs_stmt + [assign]

    def translate_stmt_Assign(self, node: ast.Assign,
                              ctx: Context) -> List[Stmt]:
        rhs_type = self.get_type(node.value, ctx)
        rhs_stmt, rhs = rhs_stmt, rhs = self.translate_expr(node.value, ctx)
        assign_stmts = []
        for target in node.targets:
            assign_stmts += self.translate_single_assign(target, rhs, rhs_type,
                                                         node, ctx)
        return rhs_stmt + assign_stmts

    def translate_single_assign(self, target: ast.AST, rhs: Expr,
                                rhs_type: PythonType, node: ast.AST,
                                ctx: Context) -> List[Stmt]:
        stmt = []
        if isinstance(target, ast.Tuple):
            if (rhs_type.name != TUPLE_TYPE or
                    len(rhs_type.type_args) != len(node.targets[0].elts)):
                raise InvalidProgramException(node, 'invalid.assign')
            # translate rhs
            for index in range(len(target.elts)):
                stmt += self.assign_to(target.elts[index], rhs,
                                       index, rhs_type,
                                       node, ctx)
            return stmt
        lhs_stmt = self.assign_to(target, rhs, None, rhs_type, node, ctx)
        return lhs_stmt

    def is_invariant(self, stmt: ast.AST) -> bool:
        return get_func_name(stmt) == 'Invariant'

    def translate_stmt_While(self, node: ast.While,
                             ctx: Context) -> List[Stmt]:
        cond_stmt, cond = self.translate_to_bool(node.test, ctx)
        if cond_stmt:
            raise InvalidProgramException(node, 'purity.violated')
        invariants = []
        locals = []
        bodyindex = 0
        while self.is_invariant(node.body[bodyindex]):
            invariants.append(self.translate_contract(node.body[bodyindex],
                                                      ctx))
            bodyindex += 1
        body = flatten(
            [self.translate_stmt(stmt, ctx) for stmt in node.body[bodyindex:]])
        body = self.translate_block(body, self.to_position(node, ctx),
                                    self.no_info(ctx))
        return [self.viper.While(cond, invariants, locals, body,
                                 self.to_position(node, ctx),
                                 self.no_info(ctx))]

    def _translate_return(self, node: ast.Return, ctx: Context) -> List[Stmt]:
        if not node.value:
            return []
        type_ = ctx.actual_function.type
        rhs_stmt, rhs = self.translate_expr(node.value, ctx)
        assign = self.viper.LocalVarAssign(
            ctx.result_var.ref,
            rhs, self.to_position(node, ctx),
            self.no_info(ctx))

        return rhs_stmt + [assign]

    def translate_stmt_Return(self, node: ast.Return,
                              ctx: Context) -> List[Stmt]:
        return_stmts = self._translate_return(node, ctx)
        tries = get_surrounding_try_blocks(ctx.actual_function.try_blocks,
                                           node)
        for try_block in tries:
            if try_block.finally_block:
                lhs = try_block.get_finally_var(self.translator).ref
                rhs = self.viper.IntLit(1, self.no_position(ctx),
                                        self.no_info(ctx))
                finally_assign = self.viper.LocalVarAssign(lhs, rhs,
                    self.no_position(ctx), self.no_info(ctx))
                label_name = ctx.get_label_name(try_block.finally_name)
                jmp = self.viper.Goto(label_name,
                                      self.to_position(node, ctx),
                                      self.no_info(ctx))
                return return_stmts + [finally_assign, jmp]
        end_label = ctx.get_label_name(END_LABEL)
        jmp_to_end = self.viper.Goto(end_label, self.to_position(node, ctx),
                                     self.no_info(ctx))
        return return_stmts + [jmp_to_end]
