"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Any


# AST abstract
Node = Any  # 'silver.ast.Node'
Stmt = Any  # 'silver.ast.Stmt'
Expr = Any  # 'silver.ast.Exp'

# AST
Program = Any  # 'silver.ast.Program'
Field = Any  # 'silver.ast.Field'
Method = Any  # 'silver.ast.Method'
Function = Any  # 'silver.ast.Function'

Domain = Any  # 'silver.ast.Domain'
DomainAxiom = Any  # 'silver.ast.DomainAxiom'
DomainFunc = Any  # 'silver.ast.DomainFunc'
DomainFuncApp = Any  # 'silver.ast.DomainFuncApp'
DomainType = Any  # 'silver.ast.DomainType'

TypeVar = Any  # 'silver.ast.TypeVar'
Type = Any  # 'silver.ast.Type'

Seqn = Any  # 'silver.ast.Seqn'

Trigger = Any  # 'silver.ast.Trigger'

Var = Any  # 'silver.ast.LocalVar'
VarDecl = Any  # 'silver.ast.LocalVarDecl'
VarAssign = Any  # 'silver.ast.LocalVarAssign'

# Error handling
AbstractSourcePosition = Any  # 'silver.ast.AbstractSourcePosition'
Position = Any  # 'silver.ast.Position'
Info = Any  # 'silver.ast.Info'

# Verification
AbstractVerificationError = Any  # 'silver.verifier.AbstractVerificationError'
AbstractErrorReason = Any  # 'silver.verifier.AbstractErrorReason'

# Counterexamples
ModelEntry = Any  # 'silver.verifier.ModelEntry'
Sort = Any  # 'silicon.state.terms.Sort'
Term = Any  # 'silicon.state.terms.Term'
