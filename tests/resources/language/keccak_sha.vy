#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

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


#@ ensures: implies(a == b, result())
@public
def hash_is_function(a: string[256], b: string[256]) -> bool:
    return sha256(a) == sha256(b)