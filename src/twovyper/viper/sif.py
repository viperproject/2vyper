"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from twovyper.viper.jvmaccess import JVM
from twovyper.viper.typedefs import Program


def configure_mpp_transformation(jvm: JVM):
    """
    Configure which optimizations to apply in MPP transformation.
    - ctrl_opt: only generate those control variables which are needed.
    - seq_opt:  bunch together statements which are executed under the same condition without
                interference with the other execution.
    - act_opt:  at the beginning of each method add an 'assume p1' statement.
    - func_opt: only apply the _checkDefined and _isDefined functions in the first execution.
    """
    transformer_object = getattr(getattr(jvm.viper.silver.sif, 'SIFExtendedTransformer$'), 'MODULE$')
    transformer_object.optimizeControlFlow(True)
    transformer_object.optimizeSequential(True)
    transformer_object.optimizeRestrictActVars(True)
    transformer_object.onlyTransformMethodsWithRelationalSpecs(True)
    transformer_object.addPrimedFuncAppReplacement("_checkDefined", "first_arg")
    transformer_object.addPrimedFuncAppReplacement("_isDefined", "true")


def transform(jvm: JVM, program: Program):
    transformer_object = getattr(getattr(jvm.viper.silver.sif, 'SIFExtendedTransformer$'), 'MODULE$')
    return transformer_object.transform(program, False)
