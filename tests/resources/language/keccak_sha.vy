#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: no_gas


use_sha: bool


#@ invariant: forall({a: bytes32, b: bytes32}, {keccak256(a), keccak256(b)}, implies(a == b, keccak256(a) == keccak256(b)))


@public
def __init__(_use_sha: bool):
    self.use_sha = _use_sha


@public
def hash(b: bytes[64]) -> bytes32:
    if self.use_sha:
        return sha256(b)
    else:
        return keccak256(b)

@public
def hash_revert(b: bytes[64]) -> bytes32:
    if self.use_sha:
        #@ assert sha256_inv(sha256(b)) == b, UNREACHABLE
        return sha256(b)
    else:
        #@ assert keccak256_inv(keccak256(b)) == b, UNREACHABLE
        return keccak256(b)

@public
def hash_revert_fail_1(b: bytes[64]) -> bytes32:
    #:: ExpectedOutput(assert.failed:assertion.false)
    #@ assert keccak256_inv(sha256(b)) == b, UNREACHABLE
    return sha256(b)


@public
def hash_revert_fail_2(b: bytes[64]) -> bytes32:
    #:: ExpectedOutput(assert.failed:assertion.false)
    #@ assert sha256_inv(keccak256(b)) == b, UNREACHABLE
    return sha256(b)


@public
def hash_revert_fail_3(b: bytes[64], c: bytes[64]) -> bytes32:
    #:: ExpectedOutput(assert.failed:assertion.false)
    #@ assert sha256_inv(sha256(b)) == c, UNREACHABLE
    return sha256(b)


#@ ensures: implies(a == b, result())
@public
def hash_is_function(a: string[256], b: string[256]) -> bool:
    return sha256(a) == sha256(b)