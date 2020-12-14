#
# The MIT License (MIT)
#
# Copyright (c) 2015 Vitalik Buterin
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

# Adapted from: https://github.com/ethereum/vyper/blob/master/examples/tokens/ERC721.vy

# @dev Implementation of ERC-721 non-fungible token standard.
# @author Ryuya Nakamura (@nrryuya)

from vyper.interfaces import ERC721

implements: ERC721

#@ config: allocation, no_performs, no_derived_wei_resource

# Interface for the contract called by safeTransferFrom()
contract ERC721Receiver:
    def onERC721Received(
            _operator: address,
            _from: address,
            _tokenId: uint256,
            _data: bytes[1024]
        ) -> bytes32: constant


# @dev Emits when ownership of any NFT changes by any mechanism. This event emits when NFTs are
#      created (`from` == 0) and destroyed (`to` == 0). Exception: during contract creation, any
#      number of NFTs may be created and assigned without emitting Transfer. At the time of any
#      transfer, the approved address for that NFT (if any) is reset to none.
# @param _from Sender of NFT (if address is zero address it indicates token creation).
# @param _to Receiver of NFT (if address is zero address it indicates token destruction).
# @param _tokenId The NFT that got transfered.
Transfer: event({
        _from: indexed(address),
        _to: indexed(address),
        _tokenId: indexed(uint256)
    })

# @dev This emits when the approved address for an NFT is changed or reaffirmed. The zero
#      address indicates there is no approved address. When a Transfer event emits, this also
#      indicates that the approved address for that NFT (if any) is reset to none.
# @param _owner Owner of NFT.
# @param _approved Address that we are approving.
# @param _tokenId NFT which we are approving.
Approval: event({
        _owner: indexed(address),
        _approved: indexed(address),
        _tokenId: indexed(uint256)
    })

# @dev This emits when an operator is enabled or disabled for an owner. The operator can manage
#      all NFTs of the owner.
# @param _owner Owner of NFT.
# @param _operator Address to which we are setting operator rights.
# @param _approved Status of operator rights(true if operator rights are given and false if
# revoked).
ApprovalForAll: event({
        _owner: indexed(address),
        _operator: indexed(address),
        _approved: bool
    })


# @dev Mapping from NFT ID to the address that owns it.
idToOwner: map(uint256, address)

# @dev Mapping from NFT ID to approved address.
idToApprovals: map(uint256, address)

# @dev Mapping from owner address to count of his tokens.
ownerToNFTokenCount: map(address, uint256)

# @dev Mapping from owner address to mapping of operator addresses.
ownerToOperators: map(address, map(address, bool))

# @dev Address of minter, who can mint a token
minter: address

# @dev Mapping of interface id to bool about whether or not it's supported
supportedInterfaces: map(bytes32, bool)

# @dev ERC165 interface ID of ERC165
ERC165_INTERFACE_ID: constant(bytes32) = 0x0000000000000000000000000000000000000000000000000000000001ffc9a7

# @dev ERC165 interface ID of ERC721
ERC721_INTERFACE_ID: constant(bytes32) = 0x0000000000000000000000000000000000000000000000000000000080ac58cd


#@ resource: token(id: uint256)
#@ resource: nothing()


#@ invariant: self.ownerToNFTokenCount[ZERO_ADDRESS] == 0
#@ invariant: forall({a: address}, {self.ownerToOperators[ZERO_ADDRESS][a]}, not self.ownerToOperators[ZERO_ADDRESS][a])

#@ invariant: forall({id: uint256}, {self.idToOwner[id]}, {self.idToApprovals[id]},
    #@ self.idToOwner[id] != ZERO_ADDRESS ==> self.idToOwner[id] != self.idToApprovals[id])
#@ invariant: forall({id: uint256}, {self.idToOwner[id]}, {self.idToApprovals[id]},
    #@ self.idToOwner[id] == ZERO_ADDRESS ==> self.idToApprovals[id] == ZERO_ADDRESS)

#@ invariant: self.minter == old(self.minter)

#@ invariant: forall({a: address}, {allocated[nothing](a)}, allocated[nothing](a) == 0)
#@ invariant: forall({a: address, id: uint256}, allocated[token(id)](a) == (1 if self.idToOwner[id] == a and a != ZERO_ADDRESS else 0))

#@ invariant: forall({id: uint256}, {allocated[creator(token(id))](self.minter)}, allocated[creator(token(id))](self.minter) == 1)
#@ invariant: forall({a: address, o: address}, {trusted(o, by=a)}, trusted(o, by=a) == self.ownerToOperators[a][o])

#@ invariant: forall({id: uint256, o: address, a: address}, {offered[token(id) <-> nothing](1, 0, o, a)},
    #@ offered[token(id) <-> nothing](1, 0, o, a) == 
        #@ (1 if a == self.idToApprovals[id] and o == self.idToOwner[id] and a != ZERO_ADDRESS and o != ZERO_ADDRESS else 0))


@public
def __init__():
    """
    @dev Contract constructor.
    """
    self.supportedInterfaces[ERC165_INTERFACE_ID] = True
    self.supportedInterfaces[ERC721_INTERFACE_ID] = True
    self.minter = msg.sender

    #@ foreach({id: uint256}, create[creator(token(id))](1))


@public
@constant
def supportsInterface(_interfaceID: bytes32) -> bool:
    """
    @dev Interface identification is specified in ERC-165.
    @param _interfaceID Id of the interface
    """
    return self.supportedInterfaces[_interfaceID]


### VIEW FUNCTIONS ###

@public
@constant
def balanceOf(_owner: address) -> uint256:
    """
    @dev Returns the number of NFTs owned by `_owner`.
         Throws if `_tokenId` is not a valid NFT. NFTs assigned to the zero address are considered invalid.
    @param _owner Address for whom to query the balance.
    """
    assert _owner != ZERO_ADDRESS
    return self.ownerToNFTokenCount[_owner]


@public
@constant
def ownerOf(_tokenId: uint256) -> address:
    """
    @dev Returns the address of the owner of the NFT. 
         Throws if `_tokenId` is not a valid NFT.
    @param _tokenId The identifier for an NFT.
    """
    owner: address = self.idToOwner[_tokenId]
    # Throws if `_tokenId` is not a valid NFT
    assert owner != ZERO_ADDRESS
    return owner


@public
@constant
def getApproved(_tokenId: uint256) -> address:
    """
    @dev Get the approved address for a single NFT.
         Throws if `_tokenId` is not a valid NFT.
    @param _tokenId ID of the NFT to query the approval of.
    """
    # Throws if `_tokenId` is not a valid NFT
    assert self.idToOwner[_tokenId] != ZERO_ADDRESS
    return self.idToApprovals[_tokenId]


@public
@constant
def isApprovedForAll(_owner: address, _operator: address) -> bool:
    """
    @dev Checks if `_operator` is an approved operator for `_owner`.
    @param _owner The address that owns the NFTs.
    @param _operator The address that acts on behalf of the owner.
    """
    return (self.ownerToOperators[_owner])[_operator]


### TRANSFER FUNCTION HELPERS ###

@private
@constant
def _isApprovedOrOwner(_spender: address, _tokenId: uint256) -> bool:
    """
    @dev Returns whether the given spender can transfer a given token ID
    @param spender address of the spender to query
    @param tokenId uint256 ID of the token to be transferred
    @return bool whether the msg.sender is approved for the given token ID, 
        is an operator of the owner, or is the owner of the token
    """
    owner: address = self.idToOwner[_tokenId]
    spenderIsOwner: bool = owner == _spender
    spenderIsApproved: bool = _spender == self.idToApprovals[_tokenId]
    spenderIsApprovedForAll: bool = (self.ownerToOperators[owner])[_spender]
    return (spenderIsOwner or spenderIsApproved) or spenderIsApprovedForAll


@private
def _addTokenTo(_to: address, _tokenId: uint256):
    """
    @dev Add a NFT to a given address
         Throws if `_tokenId` is owned by someone.
    """
    # Throws if `_tokenId` is owned by someone
    assert self.idToOwner[_tokenId] == ZERO_ADDRESS
    # Change the owner
    self.idToOwner[_tokenId] = _to
    # Change count tracking
    self.ownerToNFTokenCount[_to] += 1


@private
def _removeTokenFrom(_from: address, _tokenId: uint256):
    """
    @dev Remove a NFT from a given address
         Throws if `_from` is not the current owner.
    """
    # Throws if `_from` is not the current owner
    assert self.idToOwner[_tokenId] == _from
    # Change the owner
    self.idToOwner[_tokenId] = ZERO_ADDRESS
    # Change count tracking
    self.ownerToNFTokenCount[_from] -= 1


@private
def _clearApproval(_owner: address, _tokenId: uint256):
    """
    @dev Clear an approval of a given address
         Throws if `_owner` is not the current owner.
    """
    # Throws if `_owner` is not the current owner
    assert self.idToOwner[_tokenId] == _owner
    if self.idToApprovals[_tokenId] != ZERO_ADDRESS:
        # Reset approvals
        self.idToApprovals[_tokenId] = ZERO_ADDRESS


@private
def _transferFrom(_from: address, _to: address, _tokenId: uint256, _sender: address):
    """
    @dev Exeute transfer of a NFT. 
         Throws unless `msg.sender` is the current owner, an authorized operator, or the approved
         address for this NFT. (NOTE: `msg.sender` not allowed in private function so pass `_sender`.)
         Throws if `_to` is the zero address.
         Throws if `_from` is not the current owner.
         Throws if `_tokenId` is not a valid NFT.
    """
    # Check requirements
    assert self._isApprovedOrOwner(_sender, _tokenId)
    # Throws if `_to` is the zero address
    assert _to != ZERO_ADDRESS

    # Clear approval. Throws if `_from` is not the current owner
    self._clearApproval(_from, _tokenId)
    # Remove NFT. Throws if `_tokenId` is not a valid NFT
    self._removeTokenFrom(_from, _tokenId)
    # Add NFT
    self._addTokenTo(_to, _tokenId)

    #@ if _sender == _from or self.ownerToOperators[_from][_sender]:
        #@ revoke[token(_tokenId) <-> nothing](1, 0, to=old(self.idToApprovals[_tokenId]), acting_for=_from)
    #@ else:
        #@ exchange[token(_tokenId) <-> nothing](1, 0, _from, _sender, times=1)

    #@ reallocate[token(_tokenId)](1, to=_to, acting_for=_from if self.ownerToOperators[_from][_sender] else _sender)

    # Log the transfer
    log.Transfer(_from, _to, _tokenId)


### TRANSFER FUNCTIONS ###

@public
def transferFrom(_from: address, _to: address, _tokenId: uint256):
    """
    @dev Throws unless `msg.sender` is the current owner, an authorized operator, or the approved
         address for this NFT.
         Throws if `_from` is not the current owner.
         Throws if `_to` is the zero address.
         Throws if `_tokenId` is not a valid NFT.
    @notice The caller is responsible to confirm that `_to` is capable of receiving NFTs or else
            they maybe be permanently lost.
    @param _from The current owner of the NFT.
    @param _to The new owner.
    @param _tokenId The NFT to transfer.
    """
    self._transferFrom(_from, _to, _tokenId, msg.sender)


@public
def safeTransferFrom(
        _from: address,
        _to: address,
        _tokenId: uint256,
        _data: bytes[1024]=""
    ):
    """
    @dev Transfers the ownership of an NFT from one address to another address.
         Throws unless `msg.sender` is the current owner, an authorized operator, or the
         approved address for this NFT.
         Throws if `_from` is not the current owner.
         Throws if `_to` is the zero address.
         Throws if `_tokenId` is not a valid NFT.
         If `_to` is a smart contract, it calls `onERC721Received` on `_to` and throws if
         the return value is not `bytes4(keccak256("onERC721Received(address,address,uint256,bytes)"))`.
         NOTE: bytes4 is represented by bytes32 with padding
    @param _from The current owner of the NFT.
    @param _to The new owner.
    @param _tokenId The NFT to transfer.
    @param _data Additional data with no specified format, sent in call to `_to`.
    """
    self._transferFrom(_from, _to, _tokenId, msg.sender)
    if _to.is_contract: # check if `_to` is a contract address
        returnValue: bytes32 = ERC721Receiver(_to).onERC721Received(msg.sender, _from, _tokenId, _data)
        # Throws if transfer destination is a contract which does not implement 'onERC721Received'
        assert returnValue == method_id("onERC721Received(address,address,uint256,bytes)", bytes32)


@public
def approve(_approved: address, _tokenId: uint256):
    """
    @dev Set or reaffirm the approved address for an NFT. The zero address indicates there is no approved address. 
         Throws unless `msg.sender` is the current NFT owner, or an authorized operator of the current owner.
         Throws if `_tokenId` is not a valid NFT. (NOTE: This is not written the EIP)
         Throws if `_approved` is the current owner. (NOTE: This is not written the EIP)
    @param _approved Address to be approved for the given NFT ID.
    @param _tokenId ID of the token to be approved.
    """
    owner: address = self.idToOwner[_tokenId]
    # Throws if `_tokenId` is not a valid NFT
    assert owner != ZERO_ADDRESS
    # Throws if `_approved` is the current owner
    assert _approved != owner
    # Check requirements
    senderIsOwner: bool = self.idToOwner[_tokenId] == msg.sender
    senderIsApprovedForAll: bool = (self.ownerToOperators[owner])[msg.sender]
    assert (senderIsOwner or senderIsApprovedForAll)
    #@ revoke[token(_tokenId) <-> nothing](1, 0, to=self.idToApprovals[_tokenId], acting_for=owner)
    # Set the approval
    self.idToApprovals[_tokenId] = _approved
    #@ offer[token(_tokenId) <-> nothing](1, 0, to=_approved, acting_for=owner, times=1 if _approved != ZERO_ADDRESS else 0)
    log.Approval(owner, _approved, _tokenId)


@public
def setApprovalForAll(_operator: address, _approved: bool):
    """
    @dev Enables or disables approval for a third party ("operator") to manage all of
         `msg.sender`'s assets. It also emits the ApprovalForAll event.
         Throws if `_operator` is the `msg.sender`. (NOTE: This is not written the EIP)
    @notice This works even if sender doesn't own any tokens at the time.
    @param _operator Address to add to the set of authorized operators.
    @param _isApproved True if the operators is approved, false to revoke approval.
    """
    # Throws if `_operator` is the `msg.sender`
    assert _operator != msg.sender
    self.ownerToOperators[msg.sender][_operator] = _approved
    #@ trust(_operator, _approved)
    log.ApprovalForAll(msg.sender, _operator, _approved)


### MINT & BURN FUNCTIONS ###

@public
def mint(_to: address, _tokenId: uint256) -> bool:
    """
    @dev Function to mint tokens
         Throws if `msg.sender` is not the minter.
         Throws if `_to` is zero address.
         Throws if `_tokenId` is owned by someone.
    @param to The address that will receive the minted tokens.
    @param tokenId The token id to mint.
    @return A boolean that indicates if the operation was successful.
    """
    # Throws if `msg.sender` is not the minter
    assert msg.sender == self.minter
    # Throws if `_to` is zero address
    assert _to != ZERO_ADDRESS
    # Add NFT. Throws if `_tokenId` is owned by someone
    self._addTokenTo(_to, _tokenId)

    #@ create[token(_tokenId)](1, to=_to)

    log.Transfer(ZERO_ADDRESS, _to, _tokenId)
    return True


@public
def burn(_tokenId: uint256):
    """
    @dev Burns a specific ERC721 token.
         Throws unless `msg.sender` is the current owner, an authorized operator, or the approved
         address for this NFT.
         Throws if `_tokenId` is not a valid NFT.
    @param tokenId uint256 id of the ERC721 token to be burned.
    """
    # Check requirements
    assert self._isApprovedOrOwner(msg.sender, _tokenId)
    owner: address = self.idToOwner[_tokenId]
    # Throws if `_tokenId` is not a valid NFT
    assert owner != ZERO_ADDRESS

    #@ if msg.sender == owner or self.ownerToOperators[owner][msg.sender]:
        #@ revoke[token(_tokenId) <-> nothing](1, 0, to=self.idToApprovals[_tokenId], acting_for=owner)
    #@ else:
        #@ exchange[token(_tokenId) <-> nothing](1, 0, owner, msg.sender, times=1)
    
    self._clearApproval(owner, _tokenId)
    self._removeTokenFrom(owner, _tokenId)

    #@ destroy[token(_tokenId)](1, acting_for=owner if self.ownerToOperators[owner][msg.sender] else msg.sender)
    
    log.Transfer(owner, ZERO_ADDRESS, _tokenId)