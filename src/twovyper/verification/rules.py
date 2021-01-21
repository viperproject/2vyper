"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Dict, Tuple


"""Conversion rules from Silver level errors to 2vyper errors."""
Rule = Dict[Tuple[str, str], Tuple[str, str]]


def combine(first: Rule, second: Rule) -> Rule:
    """
    Combines `first` and `second` to produce a rule as if we first apply
    `first` and then apply `second` to its result.
    """
    res = first.copy()
    for k, v in first.items():
        # If the result of the first mapping is an input to the second mapping,
        # do the mapping
        if v in second:
            res[k] = second[v]
    # For all keys which are not mentioned in the first mapping, add the second
    # mapping
    for k, v in second.items():
        if k not in res:
            res[k] = v
    return res


INVARIANT_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('invariant.violated', 'assertion.false'),
    ('assert.failed', 'division.by.zero'):
        ('invariant.not.wellformed', 'division.by.zero'),
    ('assert.failed', 'seq.index.length'):
        ('invariant.not.wellformed', 'seq.index.length'),
    ('assert.failed', 'seq.index.negative'):
        ('invariant.not.wellformed', 'seq.index.negative')
}

LOOP_INVARIANT_BASE_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('loop.invariant.not.established', 'assertion.false'),
    ('exhale.failed', 'assertion.false'):
        ('loop.invariant.not.established', 'assertion.false'),
    ('exhale.failed', 'insufficient.permission'):
        ('loop.invariant.not.established', 'insufficient.permission'),
    ('assert.failed', 'division.by.zero'):
        ('loop.invariant.not.wellformed', 'division.by.zero'),
    ('assert.failed', 'seq.index.length'):
        ('loop.invariant.not.wellformed', 'seq.index.length'),
    ('assert.failed', 'seq.index.negative'):
        ('loop.invariant.not.wellformed', 'seq.index.negative'),
    ('exhale.failed', 'division.by.zero'):
        ('loop.invariant.not.wellformed', 'division.by.zero'),
    ('exhale.failed', 'seq.index.length'):
        ('loop.invariant.not.wellformed', 'seq.index.length'),
    ('exhale.failed', 'seq.index.negative'):
        ('loop.invariant.not.wellformed', 'seq.index.negative')
}

LOOP_INVARIANT_STEP_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('loop.invariant.not.preserved', 'assertion.false'),
    ('exhale.failed', 'assertion.false'):
        ('loop.invariant.not.preserved', 'assertion.false'),
    ('exhale.failed', 'insufficient.permission'):
        ('loop.invariant.not.preserved', 'insufficient.permission'),
    ('assert.failed', 'division.by.zero'):
        ('loop.invariant.not.wellformed', 'division.by.zero'),
    ('assert.failed', 'seq.index.length'):
        ('loop.invariant.not.wellformed', 'seq.index.length'),
    ('assert.failed', 'seq.index.negative'):
        ('loop.invariant.not.wellformed', 'seq.index.negative'),
    ('exhale.failed', 'division.by.zero'):
        ('loop.invariant.not.wellformed', 'division.by.zero'),
    ('exhale.failed', 'seq.index.length'):
        ('loop.invariant.not.wellformed', 'seq.index.length'),
    ('exhale.failed', 'seq.index.negative'):
        ('loop.invariant.not.wellformed', 'seq.index.negative')
}

POSTCONDITION_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('postcondition.violated', 'assertion.false'),
    ('exhale.failed', 'assertion.false'):
        ('postcondition.violated', 'assertion.false'),
    ('exhale.failed', 'insufficient.permission'):
        ('postcondition.violated', 'insufficient.permission'),
    ('assert.failed', 'division.by.zero'):
        ('not.wellformed', 'division.by.zero'),
    ('assert.failed', 'seq.index.length'):
        ('not.wellformed', 'seq.index.length'),
    ('assert.failed', 'seq.index.negative'):
        ('not.wellformed', 'seq.index.negative'),
    ('exhale.failed', 'division.by.zero'):
        ('not.wellformed', 'division.by.zero'),
    ('exhale.failed', 'seq.index.length'):
        ('not.wellformed', 'seq.index.length'),
    ('exhale.failed', 'seq.index.negative'):
        ('not.wellformed', 'seq.index.negative')
}

PRECONDITION_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('precondition.violated', 'assertion.false'),
    ('exhale.failed', 'assertion.false'):
        ('precondition.violated', 'assertion.false'),
    ('exhale.failed', 'insufficient.permission'):
        ('precondition.violated', 'insufficient.permission'),
    ('assert.failed', 'division.by.zero'):
        ('not.wellformed', 'division.by.zero'),
    ('assert.failed', 'seq.index.length'):
        ('not.wellformed', 'seq.index.length'),
    ('assert.failed', 'seq.index.negative'):
        ('not.wellformed', 'seq.index.negative'),
    ('exhale.failed', 'division.by.zero'):
        ('not.wellformed', 'division.by.zero'),
    ('exhale.failed', 'seq.index.length'):
        ('not.wellformed', 'seq.index.length'),
    ('exhale.failed', 'seq.index.negative'):
        ('not.wellformed', 'seq.index.negative')
}

INTERFACE_POSTCONDITION_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('postcondition.not.implemented', 'assertion.false')
}

LEMMA_FAIL = {
    ('postcondition.violated', 'assertion.false'):
        ('lemma.step.invalid', 'assertion.false'),
    ('application.precondition', 'assertion.false'):
        ('lemma.application.invalid', 'assertion.false')
}

CHECK_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('check.violated', 'assertion.false'),
    ('assert.failed', 'division.by.zero'):
        ('not.wellformed', 'division.by.zero'),
    ('assert.failed', 'seq.index.length'):
        ('not.wellformed', 'seq.index.length'),
    ('assert.failed', 'seq.index.negative'):
        ('not.wellformed', 'seq.index.negative')
}

CALL_INVARIANT_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('call.invariant', 'assertion.false')
}

DURING_CALL_INVARIANT_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('during.call.invariant', 'assertion.false')
}

CALL_CHECK_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('call.check', 'assertion.false')
}

CALLER_PRIVATE_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('caller.private.violated', 'assertion.false')
}

PRIVATE_CALL_CHECK_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('private.call.check', 'assertion.false')
}

CALL_LEAK_CHECK_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('call.leakcheck', 'allocation.leaked')
}

INHALE_INVARIANT_FAIL = {
    ('inhale.failed', 'division.by.zero'):
        ('invariant.not.wellformed', 'division.by.zero'),
    ('inhale.failed', 'seq.index.length'):
        ('invariant.not.wellformed', 'seq.index.length'),
    ('inhale.failed', 'seq.index.negative'):
        ('invariant.not.wellformed', 'seq.index.negative')
}

INHALE_CALLER_PRIVATE_FAIL = {
    ('inhale.failed', 'division.by.zero'):
        ('caller.private.not.wellformed', 'division.by.zero'),
    ('inhale.failed', 'seq.index.length'):
        ('caller.private.not.wellformed', 'seq.index.length'),
    ('inhale.failed', 'seq.index.negative'):
        ('caller.private.not.wellformed', 'seq.index.negative')
}

INHALE_LOOP_INVARIANT_FAIL = {
    ('inhale.failed', 'division.by.zero'):
        ('loop.invariant.not.wellformed', 'division.by.zero'),
    ('inhale.failed', 'seq.index.length'):
        ('loop.invariant.not.wellformed', 'seq.index.length'),
    ('inhale.failed', 'seq.index.negative'):
        ('loop.invariant.not.wellformed', 'seq.index.negative')
}

INHALE_POSTCONDITION_FAIL = {
    ('inhale.failed', 'division.by.zero'):
        ('postcondition.not.wellformed', 'division.by.zero'),
    ('inhale.failed', 'seq.index.length'):
        ('postcondition.not.wellformed', 'seq.index.length'),
    ('inhale.failed', 'seq.index.negative'):
        ('postcondition.not.wellformed', 'seq.index.negative')
}

INHALE_PRECONDITION_FAIL = {
    ('inhale.failed', 'division.by.zero'):
        ('precondition.not.wellformed', 'division.by.zero'),
    ('inhale.failed', 'seq.index.length'):
        ('precondition.not.wellformed', 'seq.index.length'),
    ('inhale.failed', 'seq.index.negative'):
        ('precondition.not.wellformed', 'seq.index.negative')
}

INHALE_INTERFACE_FAIL = {
    ('inhale.failed', 'division.by.zero'):
        ('interface.postcondition.not.wellformed', 'division.by.zero'),
    ('inhale.failed', 'seq.index.length'):
        ('interface.postcondition.not.wellformed', 'seq.index.length'),
    ('inhale.failed', 'seq.index.negative'):
        ('interface.postcondition.not.wellformed', 'seq.index.negative')
}

INVARIANT_TRANSITIVITY_VIOLATED = {
    ('assert.failed', 'assertion.false'):
        ('invariant.not.wellformed', 'transitivity.violated')
}

INVARIANT_REFLEXIVITY_VIOLATED = {
    ('assert.failed', 'assertion.false'):
        ('invariant.not.wellformed', 'reflexivity.violated')
}

POSTCONDITION_TRANSITIVITY_VIOLATED = {
    ('assert.failed', 'assertion.false'):
        ('postcondition.not.wellformed', 'transitivity.violated')
}

POSTCONDITION_REFLEXIVITY_VIOLATED = {
    ('assert.failed', 'assertion.false'):
        ('postcondition.not.wellformed', 'reflexivity.violated')
}

POSTCONDITION_CONSTANT_BALANCE = {
    ('assert.failed', 'assertion.false'):
        ('postcondition.not.wellformed', 'constant.balance')
}

PRECONDITION_IMPLEMENTS_INTERFACE = {
    ('application.precondition', 'assertion.false'):
        ('application.precondition', 'not.implements.interface')
}

INTERFACE_RESOURCE_PERFORMS = {
    ('assert.failed', 'assertion.false'):
        ('interface.resource', 'resource.address.self')
}

REALLOCATE_FAIL_INSUFFICIENT_FUNDS = {
    ('assert.failed', 'assertion.false'):
        ('reallocate.failed', 'insufficient.funds')
}

CREATE_FAIL_NOT_A_CREATOR = {
    ('assert.failed', 'assertion.false'):
        ('create.failed', 'not.a.creator')
}

DESTROY_FAIL_INSUFFICIENT_FUNDS = {
    ('assert.failed', 'assertion.false'):
        ('destroy.failed', 'insufficient.funds')
}

EXCHANGE_FAIL_NO_OFFER = {
    ('assert.failed', 'assertion.false'):
        ('exchange.failed', 'no.offer')
}

EXCHANGE_FAIL_INSUFFICIENT_FUNDS = {
    ('assert.failed', 'assertion.false'):
        ('exchange.failed', 'insufficient.funds')
}

INJECTIVITY_CHECK_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('$operation.failed', 'offer.not.injective')
}

NO_PERFORMS_FAIL = {
    ('exhale.failed', 'insufficient.permission'):
        ('$operation.failed', 'no.performs')
}

NOT_TRUSTED_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('$operation.failed', 'not.trusted')
}

REALLOCATE_FAIL = {
    ('$operation.failed', 'no.performs'):
        ('reallocate.failed', 'no.performs'),
    ('$operation.failed', 'not.trusted'):
        ('reallocate.failed', 'not.trusted')
}

CREATE_FAIL = {
    ('$operation.failed', 'offer.not.injective'):
        ('create.failed', 'offer.not.injective'),
    ('$operation.failed', 'no.performs'):
        ('create.failed', 'no.performs'),
    ('$operation.failed', 'not.trusted'):
        ('create.failed', 'not.trusted')
}

DESTROY_FAIL = {
    ('$operation.failed', 'offer.not.injective'):
        ('destroy.failed', 'offer.not.injective'),
    ('$operation.failed', 'no.performs'):
        ('destroy.failed', 'no.performs'),
    ('$operation.failed', 'not.trusted'):
        ('destroy.failed', 'not.trusted')
}

EXCHANGE_FAIL = {
    ('$operation.failed', 'no.performs'):
        ('exchange.failed', 'no.performs')
}

PAYABLE_FAIL = {
    ('$operation.failed', 'no.performs'):
        ('payable.failed', 'no.performs'),
    ('$operation.failed', 'not.trusted'):
        ('payable.failed', 'not.trusted')
}

PAYOUT_FAIL = {
    ('$operation.failed', 'no.performs'):
        ('payout.failed', 'no.performs')
}

OFFER_FAIL = {
    ('$operation.failed', 'offer.not.injective'):
        ('offer.failed', 'offer.not.injective'),
    ('$operation.failed', 'no.performs'):
        ('offer.failed', 'no.performs'),
    ('$operation.failed', 'not.trusted'):
        ('offer.failed', 'not.trusted')
}

REVOKE_FAIL = {
    ('$operation.failed', 'offer.not.injective'):
        ('revoke.failed', 'offer.not.injective'),
    ('$operation.failed', 'no.performs'):
        ('revoke.failed', 'no.performs'),
    ('$operation.failed', 'not.trusted'):
        ('revoke.failed', 'not.trusted')
}

TRUST_FAIL = {
    ('$operation.failed', 'offer.not.injective'):
        ('trust.failed', 'trust.not.injective'),
    ('$operation.failed', 'no.performs'):
        ('trust.failed', 'no.performs'),
    ('$operation.failed', 'not.trusted'):
        ('trust.failed', 'not.trusted')
}

ALLOCATE_UNTRACKED_FAIL = {
    ('$operation.failed', 'no.performs'):
        ('allocate.untracked.failed', 'no.performs')
}

ALLOCATION_LEAK_CHECK_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('leakcheck.failed', 'allocation.leaked')
}

PERFORMS_LEAK_CHECK_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('performs.leakcheck.failed', 'performs.leaked')
}

UNDERLYING_ADDRESS_SELF_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('derived.resource.invariant.failed', 'underlying.address.self')
}

UNDERLYING_ADDRESS_CONSTANT_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('derived.resource.invariant.failed', 'underlying.address.constant')
}

UNDERLYING_ADDRESS_TRUST_NO_ONE_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('derived.resource.invariant.failed', 'underlying.address.trust')
}

UNDERLYING_RESOURCE_NO_OFFERS_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('derived.resource.invariant.failed', 'underlying.resource.offers')
}

UNDERLYING_RESOURCE_NEQ_FAIL = {
    ('assert.failed', 'assertion.false'):
        ('derived.resource.invariant.failed', 'underlying.resource.eq')
}

PURE_FUNCTION_FAIL = {
    ('application.precondition', 'assertion.false'):
        ('function.failed', 'function.revert')
}
