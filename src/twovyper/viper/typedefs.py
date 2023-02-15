"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Any


# AST abstract
Node = Any  # 'silver.vyper_ast.Node'
Stmt = Any  # 'silver.vyper_ast.Stmt'
Expr = Any  # 'silver.vyper_ast.Exp'

# AST
Program = Any  # 'silver.vyper_ast.Program'
Field = Any  # 'silver.vyper_ast.Field'
Method = Any  # 'silver.vyper_ast.Method'
Function = Any  # 'silver.vyper_ast.Function'

Domain = Any  # 'silver.vyper_ast.Domain'
DomainAxiom = Any  # 'silver.vyper_ast.DomainAxiom'
DomainFunc = Any  # 'silver.vyper_ast.DomainFunc'
DomainFuncApp = Any  # 'silver.vyper_ast.DomainFuncApp'
DomainType = Any  # 'silver.vyper_ast.DomainType'

TypeVar = Any  # 'silver.vyper_ast.TypeVar'
Type = Any  # 'silver.vyper_ast.Type'

Seqn = Any  # 'silver.vyper_ast.Seqn'

Trigger = Any  # 'silver.vyper_ast.Trigger'

Var = Any  # 'silver.vyper_ast.LocalVar'
VarDecl = Any  # 'silver.vyper_ast.LocalVarDecl'
VarAssign = Any  # 'silver.vyper_ast.LocalVarAssign'

# Error handling
AbstractSourcePosition = Any  # 'silver.vyper_ast.AbstractSourcePosition'
Position = Any  # 'silver.vyper_ast.Position'
Info = Any  # 'silver.vyper_ast.Info'

# Verification
AbstractVerificationError = Any  # 'silver.verifier.AbstractVerificationError'
AbstractErrorReason = Any  # 'silver.verifier.AbstractErrorReason'

# Counterexamples
ModelEntry = Any  # 'silver.verifier.ModelEntry'
Sort = Any  # 'silicon.state.terms.Sort'
Term = Any  # 'silicon.state.terms.Term'
