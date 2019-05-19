"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List, Tuple


# AST abstract
Node = 'silver.ast.Node'
Stmt = 'silver.ast.Stmt'
Expr = 'silver.ast.Exp'
StmtsAndExpr = Tuple[List[Stmt], Expr]

# AST
Program = 'silver.ast.Program'
Field = 'silver.ast.Field'
Method = 'silver.ast.Method'

Domain = 'silver.ast.Domain'
DomainAxiom = 'silver.ast.DomainAxiom'
DomainFunc = 'silver.ast.DomainFunc'
DomainFuncApp = 'silver.ast.DomainFuncApp'
DomainType = 'silver.ast.DomainType'

Predicate = 'silver.ast.Predicate'

Function = 'silver.ast.Function'
FuncApp = 'silver.ast.FuncApp'

TypeVar = 'silver.ast.TypeVar'
Type = 'silver.ast.Type'

Seqn = 'silver.ast.Seqn'

Var = 'silver.ast.LocalVar'
VarDecl = 'silver.ast.LocalVarDecl'
VarAssign = 'silver.ast.LocalVarAssign'

# Error handling
AbstractSourcePosition = 'silver.ast.AbstractSourcePosition'
Position = 'silver.ast.Position'
Info = 'silver.ast.Info'

# Verification
AbstractVerificationError = 'silver.verifier.AbstractVerificationError'
AbstractErrorReason = 'silver.verifier.AbstractErrorReason'
