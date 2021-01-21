#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

# This file is translated Solidity contract from:
# https://github.com/vittominacori/erc1363-payable-token/blob/7f8a1530b415408c9c7e4d02a2f5891ace33e4e9/contracts/token/ERC1363/IERC1363Spender.sol

#@ config: allocation, no_derived_wei_resource, trust_casts

import tests.resources.allocation.ERC1363.IERC1363_alloc as ERC1363

#@ interface

#@ performs: exchange[ERC1363.token[ERC1363(msg.sender)] <-> ERC1363.token[ERC1363(msg.sender)]](1, 0, sender, self, times=amount)
@public
def onApprovalReceived(sender: address, amount: uint256, data: bytes[1024]) -> bytes32:
    raise "Not implemented"