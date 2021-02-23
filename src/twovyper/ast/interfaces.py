"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from twovyper.ast import names
from twovyper.ast import types
from twovyper.ast.types import ContractType, FunctionType, ArrayType


VYPER_INTERFACES = ['vyper', 'interfaces']

ERC20 = 'ERC20'
ERC721 = 'ERC721'

ERC20_FUNCTIONS = {
    'totalSupply': FunctionType([], types.VYPER_UINT256),
    'balanceOf': FunctionType([types.VYPER_ADDRESS], types.VYPER_UINT256),
    'allowance': FunctionType([types.VYPER_ADDRESS, types.VYPER_ADDRESS], types.VYPER_UINT256),
    'transfer': FunctionType([types.VYPER_ADDRESS, types.VYPER_UINT256], types.VYPER_BOOL),
    'transferFrom': FunctionType([types.VYPER_ADDRESS, types.VYPER_ADDRESS, types.VYPER_UINT256], types.VYPER_BOOL),
    'approve': FunctionType([types.VYPER_ADDRESS, types.VYPER_UINT256], types.VYPER_BOOL)
}

ERC20_MODIFIERS = {
    'totalSupply': names.CONSTANT,
    'balanceOf': names.CONSTANT,
    'allowance': names.MODIFYING,
    'transfer': names.MODIFYING,
    'transferFrom': names.MODIFYING,
    'approve': names.MODIFYING
}

_BYTES1024 = ArrayType(types.VYPER_BYTE, 1024, False)

ERC721_FUNCTIONS = {
    'supportsInterfaces': FunctionType([types.VYPER_BYTES32], types.VYPER_BOOL),
    'balanceOf': FunctionType([types.VYPER_ADDRESS], types.VYPER_UINT256),
    'ownerOf': FunctionType([types.VYPER_UINT256], types.VYPER_ADDRESS),
    'getApproved': FunctionType([types.VYPER_UINT256], types.VYPER_ADDRESS),
    'isApprovedForAll': FunctionType([types.VYPER_ADDRESS, types.VYPER_ADDRESS], types.VYPER_BOOL),
    'transferFrom': FunctionType([types.VYPER_ADDRESS, types.VYPER_ADDRESS, types.VYPER_UINT256], types.VYPER_BOOL),
    'safeTransferFrom': FunctionType([types.VYPER_ADDRESS, types.VYPER_ADDRESS, types.VYPER_UINT256, _BYTES1024], None),
    'approve': FunctionType([types.VYPER_ADDRESS, types.VYPER_UINT256], None),
    'setApprovalForAll': FunctionType([types.VYPER_ADDRESS, types.VYPER_BOOL], None)
}

ERC721_MODIFIERS = {
    'supportsInterfaces': names.CONSTANT,
    'balanceOf': names.CONSTANT,
    'ownerOf': names.CONSTANT,
    'getApproved': names.CONSTANT,
    'isApprovedForAll': names.CONSTANT,
    'transferFrom': names.MODIFYING,
    'safeTransferFrom': names.MODIFYING,
    'approve': names.MODIFYING,
    'setApprovalForAll': names.MODIFYING
}

ERC20_TYPE = ContractType(ERC20, ERC20_FUNCTIONS, ERC20_MODIFIERS)
ERC721_TYPE = ContractType(ERC721, ERC721_FUNCTIONS, ERC721_MODIFIERS)
