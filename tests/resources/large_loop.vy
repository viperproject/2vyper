
NUM_TOKENS: constant(int128) = 100

idToOwner: map(uint256, address)
ownerToNFTokenCount: map(address, uint256)

#@ invariant: self.ownerToNFTokenCount[ZERO_ADDRESS] == 0

@public
def __init__(_recipients: address[NUM_TOKENS], _tokenIds: uint256[NUM_TOKENS]):
  for i in range(NUM_TOKENS):
    # stop as soon as there is a non-specified recipient
    assert _recipients[i] != ZERO_ADDRESS
    self.idToOwner[_tokenIds[i]] = _recipients[i]
    self.ownerToNFTokenCount[_recipients[i]] += 1