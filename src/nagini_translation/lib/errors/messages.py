"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

"""Conversion of errors to human readable messages."""

import ast
from nagini_translation.lib.util import (
    get_containing_member,
    get_target_name,
    pprint,
)


ERRORS = {
    'assignment.failed':
        lambda i: 'Assignment might fail.',
    'call.failed':
        lambda i: 'Method call might fail.',
    'not.wellformed':
        lambda i: 'Contract might not be well-formed.',
    'call.invariant':
        lambda i: f"An invariant might not hold before the call {pprint(i.node)}.",
    'call.precondition':
        lambda i: f"The precondition of function {pprint(i.node)} might not hold.",
    'application.precondition':
        lambda i: (f"The precondition of function {i.function} might not hold."
                   if isinstance(i.node, (ast.Call, ast.FunctionDef)) else
                   'The precondition of {} might not hold.'.format(pprint(i.node))),
    'exhale.failed':
        lambda i: 'Exhale might fail.',
    'inhale.failed':
        lambda i: 'Inhale might fail.',
    'if.failed':
        lambda i: 'Conditional statement might fail.',
    'while.failed':
        lambda i: 'While statement might fail.',
    'assert.failed':
        lambda i: 'Assert might fail.',
    'postcondition.violated':
        lambda i: f"Postcondition of {i.function} might not hold.",
    'invariant.violated':
        lambda i: f"Invariant not preserved by {i.function}.",
    'fold.failed':
        lambda i: 'Fold might fail.',
    'unfold.failed':
        lambda i: 'Unfold might fail.',
    'invariant.not.preserved':
        lambda i: 'Loop invariant might not be preserved.',
    'invariant.not.established':
        lambda i: 'Loop invariant might not hold on entry.',
    'function.not.wellformed':
        lambda i: ('Function {} might not be '
                   'well-formed.').format(get_containing_member(n).name),
    'predicate.not.wellformed':
        lambda i: ('Predicate {} might not be '
                   'well-formed.').format(get_containing_member(n).name),
    'termination_check.failed':
        lambda i: 'Operation might not terminate.',
    'leak_check.failed':
        lambda i: 'Obligation leak check failed.',
    'internal':
        lambda i: 'An internal error occurred.',
    'expression.undefined':
        lambda i: 'Expression {} may not be defined.'.format(pprint(i.node)),
    'thread.creation.failed':
        lambda i: 'Thread creation may fail.',
    'thread.start.failed':
        lambda i: 'Thread start may fail.',
    'thread.join.failed':
        lambda i: 'Thread join may fail.',
    'termination_channel_check.failed':
        lambda i: 'Termination channel might exist.',
    'lock.invariant.not.established':
        lambda i: 'Lock invariant might not hold.',
}

REASONS = {
    'assertion.false':
        lambda i: 'Assertion {} might not hold.'.format(pprint(i.node)),
    'receiver.null':
        lambda i: 'Receiver of {} might be null.'.format(pprint(i.node)),
    'division.by.zero':
        lambda i: 'Divisor {} might be zero.'.format(pprint(i.node)),
    'seq.index.length':
        lambda i: f"Index {pprint(i.node)} might exceed sequence length.",
    'negative.permission':
        lambda i: 'Fraction {} might be negative.'.format(pprint(i.node)),
    'insufficient.permission':
        lambda i: ('There might be insufficient permission to '
                   'access {}.').format(pprint(i.node)),
    'termination_measure.non_positive':
        lambda i: ('Termination measure {} might be '
                   'non-positive.').format(pprint(i.node)),
    'measure.non_decreasing':
        lambda i: ('Termination measure of {} might be not '
                   'smaller.').format(pprint(i.node)),
    'gap.enabled':
        lambda i: ('Gap {} might be enabled in terminating IO '
                   'operation.').format(pprint(i.node)),
    'child_termination.not_implied':
        lambda i: ('Parent IO operation termination condition does not '
                   'imply {} termination condition.').format(pprint(i.node)),
    'obligation_measure.non_positive':
        lambda i: ('Obligation {} measure might be '
                   'non-positive.').format(pprint(i.node)),
    'must_terminate.not_taken':
        lambda i: ('Callee {} might not take MustTerminate '
                   'obligation.').format(get_target_name(n)),
    'must_terminate.loop_not_promised':
        lambda i: ('Loop might not promise to terminate.'),
    'must_terminate.loop_promise_not_kept':
        lambda i: ('Loop might not keep promise to terminate.'),
    'caller.has_unsatisfied_obligations':
        lambda i: ('Callee {} might not take all unsatisfied obligations '
                   'from the caller.'.format(get_target_name(n))),
    'method_body.leaks_obligations':
        lambda i: ('Body of method {} might leak '
                   'obligations.'.format(get_target_name(n))),
    'loop_context.has_unsatisfied_obligations':
        lambda i: ('Loop might not take all unsatisfied obligations '
                   'from the context.'),
    'loop_body.leaks_obligations':
        lambda i: ('Loop body might leak obligations.'),
    'loop_condition.not_framed_for_obligation_use':
        lambda i: ('Loop condition part {} is not framed at the point where '
                   'obligation is used.'.format(pprint(i.node))),
    'undefined.local.variable':
        lambda i: 'Local variable may not have been defined.',
    'undefined.global.name':
        lambda i: 'Global name may not have been defined.',
    'missing.dependencies':
        lambda i: 'Global dependencies may not be defined.',
    'internal':
        lambda i: 'Internal Viper error.',
    'receiver.not.injective':
        lambda i: 'Receiver expression of quantified permission is not injective.',
    'wait.level.invalid':
        lambda i: 'Thread level may not be lower than current thread.',
    'thread.not.joinable':
        lambda i: 'Thread may not be joinable.',
    'invalid.argument.type':
        lambda i: 'Thread argument may not fit target method parameter type.',
    'method.not.listed':
        lambda i: "Thread's target method may not be listed in start statement.",
    'missing.start.permission':
        lambda i: 'May not have permission to start thread.',
    'sif.fold':
        lambda i: 'The low parts of predicate {} might not hold.'.format(
            get_target_name(n.args[0])),
    'sif.unfold':
        lambda i: 'The low parts of predicate {} might not hold.'.format(
            get_target_name(n.args[0])),
    'sif_termination.condition_not_low':
        lambda i: 'Termination condition {} might not be low.'.format(pprint(n.args[0])),
    'sif_termination.not_lowevent':
        lambda i: ('Termination condition {} evaluating to false might not imply that '
                   'both executions don\'t terminate.').format(pprint(n.args[0])),
    'sif_termination.condition_not_tight':
        lambda i: 'Termination condition {} might not be tight.'.format(pprint(n.args[0])),
}

VAGUE_REASONS = {
    'assertion.false': '',
    'receiver.null': 'Receiver might be null.',
    'division.by.zero': 'Divisor might be zero.',
    'negative.permission': 'Fraction might be negative.',
    'insufficient.permission': 'There might be insufficient permission.',
    'termination_measure.non_positive': 'Termination measure might be non-positive.',
    'measure.non_decreasing': 'Termination measure might not be smaller.',
    'gap.enabled': 'Gap might be enabled in terminating IO operation.',
    'child_termination.not_implied': ('Parent IO operation termination condition does '
                                      'not imply termination condition.'),
    'obligation_measure.non_positive': 'Obligation measure might be non-positive.',
    'must_terminate.not_taken': 'Callee might not take MustTerminate obligation.',
    'caller.has_unsatisfied_obligations': ('Callee might not take all unsatisfied '
                                           'obligations from the caller.'),
    'method_body.leaks_obligations': 'Method body might leak obligations.',
    'loop_condition.not_framed_for_obligation_use': ('Loop condition part is not framed '
                                                     'at the point where obligation is '
                                                     'used.'),
}
