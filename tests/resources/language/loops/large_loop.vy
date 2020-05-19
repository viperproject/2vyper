#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

NUM_TOKENS: constant(int128) = 99

idToOwner: map(uint256, address)
ownerToNFTokenCount: map(address, uint256)

#@ invariant: self.ownerToNFTokenCount[ZERO_ADDRESS] == 0

@public
def __init__(_recipients: address[NUM_TOKENS], _tokenIds: uint256[NUM_TOKENS]):
  for i in range(NUM_TOKENS):
    #@ invariant: self.ownerToNFTokenCount[ZERO_ADDRESS] == 0
    # stop as soon as there is a non-specified recipient
    assert _recipients[i] != ZERO_ADDRESS
    self.idToOwner[_tokenIds[i]] = _recipients[i]
    self.ownerToNFTokenCount[_recipients[i]] += 1