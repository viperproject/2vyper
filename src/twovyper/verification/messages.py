"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

# Conversion of errors to human readable messages.

from twovyper.ast.text import pprint


ERRORS = {
    'assignment.failed':
        lambda i: "Assignment might fail.",
    'call.failed':
        lambda i: "Method call might fail.",
    'not.wellformed':
        lambda i: f"Function {i.function.name} might not be well-formed.",
    'call.invariant':
        lambda i: f"An invariant might not hold before the call {pprint(i.node)}.",
    'after.call.invariant':
        lambda i: f"An invariant might not hold after the call {pprint(i.node)}.",
    'during.call.invariant':
        lambda i: f"An invariant might not hold during the call {pprint(i.node)}.",
    'call.check':
        lambda i: f"A check might not hold before the call {pprint(i.node)}.",
    'private.call.check':
        lambda i: f"A check might not hold in the private function.",
    'call.precondition':
        lambda i: f"The precondition of function {pprint(i.node)} might not hold.",
    'call.leakcheck':
        lambda i: f"The leak check for call {pprint(i.node)} might not hold.",
    'application.precondition':
        lambda i: f"The precondition of function {pprint(i.node)} might not hold.",
    'exhale.failed':
        lambda i: "Exhale might fail.",
    'inhale.failed':
        lambda i: "Inhale might fail.",
    'if.failed':
        lambda i: "Conditional statement might fail.",
    'while.failed':
        lambda i: "While statement might fail.",
    'assert.failed':
        lambda i: "Assert might fail.",
    'postcondition.violated':
        lambda i: f"Postcondition of {i.function.name} might not hold.",
    'postcondition.not.implemented':
        lambda i: f"Function {i.function.name} might not correctly implement an interface.",
    'precondition.violated':
        lambda i: f"Precondition of {i.function.name} might not hold.",
    'invariant.violated':
        lambda i: f"Invariant not preserved by {i.function.name}.",
    'loop.invariant.not.established':
        lambda i: f"Loop invariant not established.",
    'loop.invariant.not.preserved':
        lambda i: f"Loop invariant not preserved.",
    'check.violated':
        lambda i: f"A check might not hold after the body of {i.function.name}.",
    'caller.private.violated':
        lambda i: f"A caller private expression might got changed for another caller.",
    'caller.private.not.wellformed':
        lambda i: f"Caller private {pprint(i.node)} might not be well-formed.",
    'invariant.not.wellformed':
        lambda i: f"Invariant {pprint(i.node)} might not be well-formed.",
    'loop.invariant.not.wellformed':
        lambda i: f"Loop invariant {pprint(i.node)} might not be well-formed.",
    'postcondition.not.wellformed':
        lambda i: f"(General) Postcondition {pprint(i.node)} might not be well-formed.",
    'precondition.not.wellformed':
        lambda i: f"Precondition {pprint(i.node)} might not be well-formed.",
    'interface.postcondition.not.wellformed':
        lambda i: f"Postcondition of {pprint(i.node)} might not be well-formed.",
    'reallocate.failed':
        lambda i: f"Reallocate might fail.",
    'create.failed':
        lambda i: f"Create might fail.",
    'destroy.failed':
        lambda i: f"Destroy might fail.",
    'offer.failed':
        lambda i: f"Offer might fail.",
    'revoke.failed':
        lambda i: f"Revoke might fail.",
    'exchange.failed':
        lambda i: f"Exchange {pprint(i.node)} might fail.",
    'trust.failed':
        lambda i: f"Trust might fail.",
    'leakcheck.failed':
        lambda i: f"Leak check for resource {i.resource.name} might fail in {i.function.name}.",
    'performs.leakcheck.failed':
        lambda i: f"Leakcheck for performs clauses might fail.",
    'fold.failed':
        lambda i: "Fold might fail.",
    'unfold.failed':
        lambda i: "Unfold might fail.",
    'invariant.not.preserved':
        lambda i: "Loop invariant might not be preserved.",
    'invariant.not.established':
        lambda i: "Loop invariant might not hold on entry.",
    'function.not.wellformed':
        lambda i: "Function might not be well-formed.",
    'predicate.not.wellformed':
        lambda i: "Predicate might not be well-formed.",
    'function.failed':
        lambda i: f"The function call {pprint(i.node)} might not succeed."
}

REASONS = {
    'assertion.false':
        lambda i: f"Assertion {pprint(i.node)} might not hold.",
    'transitivity.violated':
        lambda i: f"It might not be transitive.",
    'reflexivity.violated':
        lambda i: f"It might not be reflexive.",
    'constant.balance':
        lambda i: f"It might assume constant balance.",
    'division.by.zero':
        lambda i: f"Divisor {pprint(i.node)} might be zero.",
    'seq.index.length':
        lambda i: f"Index {pprint(i.node)} might exceed array length.",
    'seq.index.negative':
        lambda i: f"Index {pprint(i.node)} might be negative.",
    'not.implements.interface':
        lambda i: f"Receiver might not implement the interface.",
    'insufficient.funds':
        lambda i: f"There might be insufficient allocated funds.",
    'not.a.creator':
        lambda i: f"There might not be an appropriate creator resource.",
    'not.trusted':
        lambda i: f"Message sender might not be trusted.",
    'no.offer':
        lambda i: f"There might not be an appropriate offer.",
    'no.performs':
        lambda i: f"The function might not be allowed to perform this operation.",
    'offer.not.injective':
        lambda i: f"The offer might not be injective.",
    'trust.not.injective':
        lambda i: f"Trust might not be injective.",
    'allocation.leaked':
        lambda i: f"Some allocation might be leaked.",
    'performs.leaked':
        lambda i: f"The function might not perform all required operations.",
    'receiver.not.injective':
        lambda i: f"Receiver of {pprint(i.node)} might not be injective.",
    'receiver.null':
        lambda i: f"Receiver of {pprint(i.node)} might be null.",
    'negative.permission':
        lambda i: f"Fraction {pprint(i.node)} might be negative.",
    'insufficient.permission':
        lambda i: f"There might be insufficient permission to access {pprint(i.node)}.",
    'function.revert':
        lambda i: f"The function {i.function.name} might revert."

}
