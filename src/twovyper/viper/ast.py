"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from jpype import JImplements, JOverride


class ViperAST:
    """
    Provides convenient access to the classes which constitute the Viper AST.
    All constructors convert Python lists to Scala sequences, Python ints
    to Scala BigInts, and wrap Scala Option types where necessary.
    """

    def __init__(self, jvm):
        self.jvm = jvm
        self.java = jvm.java
        self.scala = jvm.scala
        self.ast = jvm.viper.silver.ast
        self.ast_extensions = jvm.viper.silver.sif

        def getobject(package, name):
            return getattr(getattr(package, name + '$'), 'MODULE$')

        def getconst(name):
            return getobject(self.ast, name)

        self.QPs = getobject(self.ast.utility, 'QuantifiedPermissions')
        self.AddOp = getconst('AddOp')
        self.AndOp = getconst('AndOp')
        self.DivOp = getconst('DivOp')
        self.FracOp = getconst('FracOp')
        self.GeOp = getconst('GeOp')
        self.GtOp = getconst('GtOp')
        self.ImpliesOp = getconst('ImpliesOp')
        self.IntPermMulOp = getconst('IntPermMulOp')
        self.LeOp = getconst('LeOp')
        self.LtOp = getconst('LtOp')
        self.ModOp = getconst('ModOp')
        self.MulOp = getconst('MulOp')
        self.NegOp = getconst('NegOp')
        self.NotOp = getconst('NotOp')
        self.OrOp = getconst('OrOp')
        self.PermAddOp = getconst('PermAddOp')
        self.PermDivOp = getconst('PermDivOp')
        self.SubOp = getconst('SubOp')
        self.NoPosition = getconst('NoPosition')
        self.NoInfo = getconst('NoInfo')
        self.NoTrafos = getconst('NoTrafos')
        self.Int = getconst('Int')
        self.Bool = getconst('Bool')
        self.Ref = getconst('Ref')
        self.Perm = getconst('Perm')
        self.MethodWithLabelsInScope = getobject(self.ast, 'MethodWithLabelsInScope')
        self.BigInt = getobject(self.scala.math, 'BigInt')
        self.None_ = getobject(self.scala, 'None')
        self.seq_types = set()

    def is_available(self) -> bool:
        """
        Checks if the Viper AST is available, i.e., silver is on the Java classpath.
        """
        return self.jvm.is_known_class(self.ast.Program)

    def is_extension_available(self) -> bool:
        """
        Checks if the extended AST is available, i.e., the SIF AST extension is on the
        Java classpath.
        """
        return self.jvm.is_known_class(self.ast_extensions.SIFReturnStmt)

    def empty_seq(self):
        return self.scala.collection.mutable.ListBuffer()

    def singleton_seq(self, element):
        result = self.scala.collection.mutable.ArraySeq(1)
        result.update(0, element)
        return result

    def append(self, list, to_append):
        if to_append is not None:
            lsttoappend = self.singleton_seq(to_append)
            list.append(lsttoappend)

    def to_seq(self, py_iterable):
        result = self.scala.collection.mutable.ArraySeq(len(py_iterable))
        for index, value in enumerate(py_iterable):
            result.update(index, value)
        return result.toList()

    def to_list(self, seq):
        result = []
        iterator = seq.toIterator()
        while iterator.hasNext():
            result.append(iterator.next())
        return result

    def to_map(self, dict):
        result = self.scala.collection.immutable.HashMap()
        for k, v in dict.items():
            result = result.updated(k, v)
        return result

    def to_big_int(self, num: int):
        # Python ints might not fit into a C int, therefore we use a String
        num_str = str(num)
        return self.BigInt.apply(num_str)

    def Program(self, domains, fields, functions, predicates, methods, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Program(self.to_seq(domains), self.to_seq(fields),
                                self.to_seq(functions), self.to_seq(predicates),
                                self.to_seq(methods), self.to_seq([]),
                                position, info, self.NoTrafos)

    def Function(self, name, args, type, pres, posts, body, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        body = self.scala.Some(body) if body is not None else self.None_
        return self.ast.Function(name, self.to_seq(args), type,
                                 self.to_seq(pres),
                                 self.to_seq(posts),
                                 body, position, info, self.NoTrafos)

    def Method(self, name, args, returns, pres, posts, locals, body, position=None,
               info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo

        if body is None:
            body_with_locals = self.None_
        else:
            body_with_locals = self.scala.Some(self.Seqn(body, position, info, locals))
        method = self.MethodWithLabelsInScope
        return method.apply(name, self.to_seq(args), self.to_seq(returns),
                            self.to_seq(pres), self.to_seq(posts),
                            body_with_locals, position, info,
                            self.NoTrafos)

    def Field(self, name, type, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Field(name, type, position, info, self.NoTrafos)

    def Predicate(self, name, args, body, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        body = self.scala.Some(body) if body is not None else self.None_
        return self.ast.Predicate(name, self.to_seq(args),
                                  body, position, info, self.NoTrafos)

    def PredicateAccess(self, args, pred_name, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.PredicateAccess(self.to_seq(args), pred_name, position,
                                        info, self.NoTrafos)

    def PredicateAccessPredicate(self, loc, perm, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.PredicateAccessPredicate(loc, perm, position, info, self.NoTrafos)

    def Fold(self, predicate, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Fold(predicate, position, info, self.NoTrafos)

    def Unfold(self, predicate, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Unfold(predicate, position, info, self.NoTrafos)

    def Unfolding(self, predicate, expr, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Unfolding(predicate, expr, position, info, self.NoTrafos)

    def SeqType(self, element_type):
        self.seq_types.add(element_type)
        return self.ast.SeqType(element_type)

    def SetType(self, element_type):
        return self.ast.SetType(element_type)

    def MultisetType(self, element_type):
        return self.ast.MultisetType(element_type)

    def Domain(self, name, functions, axioms, typevars, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Domain(name, self.to_seq(functions),
                               self.to_seq(axioms), self.to_seq(typevars),
                               position, info, self.NoTrafos)

    def DomainFunc(self, name, args, type, unique, domain_name, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.DomainFunc(name, self.to_seq(args), type, unique,
                                   position, info, domain_name, self.NoTrafos)

    def DomainAxiom(self, name, expr, domain_name, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.NamedDomainAxiom(name, expr, position, info, domain_name,
                                         self.NoTrafos)

    def DomainType(self, name, type_vars_map, type_vars):
        map = self.to_map(type_vars_map)
        seq = self.to_seq(type_vars)
        return self.ast.DomainType(name, map,
                                   seq)

    def DomainFuncApp(self, func_name, args, type_passed,
                      position, info, domain_name, type_var_map={}):
        position = position or self.NoPosition
        info = info or self.NoInfo

        type_passed_func = self.to_function0(type_passed)
        result = self.ast.DomainFuncApp(func_name, self.to_seq(args),
                                        self.to_map(type_var_map), position,
                                        info, type_passed_func,
                                        domain_name, self.NoTrafos)
        return result

    def TypeVar(self, name):
        return self.ast.TypeVar(name)

    def MethodCall(self, method_name, args, targets, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.MethodCall(method_name, self.to_seq(args),
                                   self.to_seq(targets), position, info, self.NoTrafos)

    def NewStmt(self, lhs, fields, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.NewStmt(lhs, self.to_seq(fields), position, info, self.NoTrafos)

    def Label(self, name, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Label(name, self.to_seq([]), position, info, self.NoTrafos)

    def Goto(self, name, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Goto(name, position, info, self.NoTrafos)

    def Seqn(self, body, position=None, info=None, locals=[]):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Seqn(self.to_seq(body), self.to_seq(locals), position, info,
                             self.NoTrafos)

    def LocalVarAssign(self, lhs, rhs, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.LocalVarAssign(lhs, rhs, position, info, self.NoTrafos)

    def FieldAssign(self, lhs, rhs, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.FieldAssign(lhs, rhs, position, info, self.NoTrafos)

    def FieldAccess(self, receiver, field, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.FieldAccess(receiver, field, position, info, self.NoTrafos)

    def FieldAccessPredicate(self, fieldacc, perm, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.FieldAccessPredicate(fieldacc, perm, position, info, self.NoTrafos)

    def Old(self, expr, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Old(expr, position, info, self.NoTrafos)

    def LabelledOld(self, expr, label, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.LabelledOld(expr, label, position, info, self.NoTrafos)

    def Inhale(self, expr, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Inhale(expr, position, info, self.NoTrafos)

    def Exhale(self, expr, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Exhale(expr, position, info, self.NoTrafos)

    def InhaleExhaleExp(self, inhale, exhale, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.InhaleExhaleExp(inhale, exhale, position, info, self.NoTrafos)

    def Assert(self, expr, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Assert(expr, position, info, self.NoTrafos)

    def FullPerm(self, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.FullPerm(position, info, self.NoTrafos)

    def NoPerm(self, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.NoPerm(position, info, self.NoTrafos)

    def WildcardPerm(self, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.WildcardPerm(position, info, self.NoTrafos)

    def FractionalPerm(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.FractionalPerm(left, right, position, info, self.NoTrafos)

    def CurrentPerm(self, location, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.CurrentPerm(location, position, info, self.NoTrafos)

    def ForPerm(self, variables, access, body, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.ForPerm(self.to_seq(variables), access, body, position, info, self.NoTrafos)

    def PermMinus(self, exp, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.PermMinus(exp, position, info, self.NoTrafos)

    def PermAdd(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.PermAdd(left, right, position, info, self.NoTrafos)

    def PermSub(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.PermSub(left, right, position, info, self.NoTrafos)

    def PermMul(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.PermMul(left, right, position, info, self.NoTrafos)

    def IntPermMul(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.IntPermMul(left, right, position, info, self.NoTrafos)

    def PermDiv(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.PermDiv(left, right, position, info, self.NoTrafos)

    def PermLtCmp(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.PermLtCmp(left, right, position, info, self.NoTrafos)

    def PermLeCmp(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.PermLeCmp(left, right, position, info, self.NoTrafos)

    def PermGtCmp(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.PermGtCmp(left, right, position, info, self.NoTrafos)

    def PermGeCmp(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.PermGeCmp(left, right, position, info, self.NoTrafos)

    def Not(self, expr, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Not(expr, position, info, self.NoTrafos)

    def Minus(self, expr, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Minus(expr, position, info, self.NoTrafos)

    def CondExp(self, cond, then, els, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.CondExp(cond, then, els, position, info, self.NoTrafos)

    def EqCmp(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.EqCmp(left, right, position, info, self.NoTrafos)

    def NeCmp(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.NeCmp(left, right, position, info, self.NoTrafos)

    def GtCmp(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.GtCmp(left, right, position, info, self.NoTrafos)

    def GeCmp(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.GeCmp(left, right, position, info, self.NoTrafos)

    def LtCmp(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.LtCmp(left, right, position, info, self.NoTrafos)

    def LeCmp(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.LeCmp(left, right, position, info, self.NoTrafos)

    def IntLit(self, num, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.IntLit(self.to_big_int(num), position, info, self.NoTrafos)

    def Implies(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Implies(left, right, position, info, self.NoTrafos)

    def FuncApp(self, name, args, position=None, info=None, type=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.FuncApp(name, self.to_seq(args), position, info, type, self.NoTrafos)

    def ExplicitSeq(self, elems, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.ExplicitSeq(self.to_seq(elems), position, info, self.NoTrafos)

    def ExplicitSet(self, elems, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.ExplicitSet(self.to_seq(elems), position, info, self.NoTrafos)

    def ExplicitMultiset(self, elems, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.ExplicitMultiset(self.to_seq(elems), position, info, self.NoTrafos)

    def EmptySeq(self, type, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.EmptySeq(type, position, info, self.NoTrafos)

    def EmptySet(self, type, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.EmptySet(type, position, info, self.NoTrafos)

    def EmptyMultiset(self, type, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.EmptyMultiset(type, position, info, self.NoTrafos)

    def LocalVarDecl(self, name, type, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.LocalVarDecl(name, type, position, info, self.NoTrafos)

    def LocalVar(self, name, type, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.LocalVar(name, type, position, info, self.NoTrafos)

    def Result(self, type, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Result(type, position, info, self.NoTrafos)

    def AnySetContains(self, elem, s, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.AnySetContains(elem, s, position, info, self.NoTrafos)

    def AnySetUnion(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.AnySetUnion(left, right, position, info, self.NoTrafos)

    def AnySetSubset(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.AnySetSubset(left, right, position, info, self.NoTrafos)

    def SeqAppend(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.SeqAppend(left, right, position, info, self.NoTrafos)

    def SeqContains(self, elem, s, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.SeqContains(elem, s, position, info, self.NoTrafos)

    def SeqLength(self, s, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.SeqLength(s, position, info, self.NoTrafos)

    def SeqIndex(self, s, ind, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.SeqIndex(s, ind, position, info, self.NoTrafos)

    def SeqTake(self, s, end, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.SeqTake(s, end, position, info, self.NoTrafos)

    def SeqDrop(self, s, end, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.SeqDrop(s, end, position, info, self.NoTrafos)

    def SeqUpdate(self, s, ind, elem, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.SeqUpdate(s, ind, elem, position, info, self.NoTrafos)

    def Add(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Add(left, right, position, info, self.NoTrafos)

    def Sub(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Sub(left, right, position, info, self.NoTrafos)

    def Mul(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Mul(left, right, position, info, self.NoTrafos)

    def Div(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Div(left, right, position, info, self.NoTrafos)

    def Mod(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Mod(left, right, position, info, self.NoTrafos)

    def And(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.And(left, right, position, info, self.NoTrafos)

    def Or(self, left, right, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Or(left, right, position, info, self.NoTrafos)

    def If(self, cond, thn, els, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        thn_seqn = self.Seqn(thn, position)
        els_seqn = self.Seqn(els, position)
        return self.ast.If(cond, thn_seqn, els_seqn, position, info, self.NoTrafos)

    def TrueLit(self, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.TrueLit(position, info, self.NoTrafos)

    def FalseLit(self, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.FalseLit(position, info, self.NoTrafos)

    def NullLit(self, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.NullLit(position, info, self.NoTrafos)

    def Forall(self, variables, triggers, exp, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo

        if not variables:
            return exp

        res = self.ast.Forall(self.to_seq(variables), self.to_seq(triggers), exp, position, info, self.NoTrafos)
        if res.isPure():
            return res
        else:
            desugared = self.to_list(self.QPs.desugarSourceQuantifiedPermissionSyntax(res))
            result = self.TrueLit(position, info)
            for qp in desugared:
                result = self.And(result, qp, position, info)
            return result

    def Exists(self, variables, triggers, exp, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        res = self.ast.Exists(self.to_seq(variables), self.to_seq(triggers), exp, position, info, self.NoTrafos)
        return res

    def Trigger(self, exps, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Trigger(self.to_seq(exps), position, info, self.NoTrafos)

    def While(self, cond, invariants, locals, body, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        body_with_locals = self.Seqn(body, position, info, locals)
        return self.ast.While(cond, self.to_seq(invariants),
                              body_with_locals, position, info, self.NoTrafos)

    def Let(self, variable, exp, body, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast.Let(variable, exp, body, position, info, self.NoTrafos)

    def from_option(self, option):
        if option == self.None_:
            return None
        else:
            return option.get()

    def to_function0(self, value):

        @JImplements(self.jvm.scala.Function0)
        class Function0:
            @JOverride
            def apply(self):
                return value

        return Function0()

    def SimpleInfo(self, comments):
        return self.ast.SimpleInfo(self.to_seq(comments))

    def ConsInfo(self, head, tail):
        return self.ast.ConsInfo(head, tail)

    def to_position(self, expr, id: str):
        path = self.java.nio.file.Paths.get(expr.file, [])
        start = self.ast.LineColumnPosition(expr.lineno, expr.col_offset)
        end = self.ast.LineColumnPosition(expr.end_lineno, expr.end_col_offset)
        end = self.scala.Some(end)
        return self.ast.IdentifierPosition(path, start, end, id)

    def is_heap_dependent(self, expr) -> bool:
        """
        Checks if the given expression contains an access to a heap location.
        Does NOT check for calls to heap-dependent functions.
        """
        for n in [expr] + self.to_list(expr.subnodes()):
            if isinstance(n, self.ast.LocationAccess):
                return True
        return False

    # SIF extension AST nodes

    def Low(self, expr, comparator: str = '', type_vars_map={}, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        comp = self.scala.Some(comparator) if comparator else self.None_
        type_vars_map = self.to_map(type_vars_map)
        return self.ast_extensions.SIFLowExp(expr, comp, type_vars_map, position, info, self.NoTrafos)

    def LowEvent(self, position=None, info=None):
        position = position or self.NoPosition
        info = info or self.NoInfo
        return self.ast_extensions.SIFLowEventExp(position, info, self.NoTrafos)
