#
# The MIT License (MIT)
# 
# Copyright (c) 2015 Maran Hidskes
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

# Adapted from https://github.com/maran/notareth


struct DocumentTransfer:
    block_number: uint256
    hash: bytes32
    frm: address
    to: address


Document: event({block_number: uint256, hash: bytes32, frm: address, to: address})

owner: address

latest_document: public(uint256)
history: public(map(uint256, DocumentTransfer))

used_hashes: map(bytes32, bool)
document_hashes: map(bytes32, address)


#@ invariant: forall({bb: bytes32}, {self.document_hashes[bb]}, {self.used_hashes[bb]},
    #@ self.document_hashes[bb] != ZERO_ADDRESS ==> self.used_hashes[bb])

#@ always check: forall({bb: bytes32}, {self.document_hashes[bb]},
    #@ self.document_hashes[bb] != old(self.document_hashes[bb]) ==>
        #@ not old(self.used_hashes[bb]) or msg.sender == old(self.document_hashes[bb]))

#@ invariant: self.latest_document >= old(self.latest_document)
#@ invariant: forall({i: uint256}, {self.history[i]},
    #@ i <= old(self.latest_document) ==> self.history[i] == old(self.history[i]))

#@ always check: forall({i: uint256}, {self.history[i]},
    #@ self.history[i] != old(self.history[i]) ==>
        #@ event(Document(self.history[i].block_number, self.history[i].hash, self.history[i].frm, self.history[i].to)))


@public
def __init__():
    self.owner = msg.sender


@private
@constant 
def _document_exists(hash: bytes32) -> bool:
    return self.used_hashes[hash]


@private
def _create_history(hash: bytes32, frm: address, to: address):
    self.latest_document += 1
    self.document_hashes[hash] = to
    self.used_hashes[hash] = True
    self.history[self.latest_document] = DocumentTransfer({block_number: block.number, hash: hash, frm: frm, to: to})
    log.Document(block.number, hash, frm, to)


@public
def new_document(hash: bytes32):
    assert not self._document_exists(hash)
    self._create_history(hash, msg.sender, msg.sender)


@public
def transfer_document(hash: bytes32, recipient: address):
    assert self._document_exists(hash)
    assert self.document_hashes[hash] == msg.sender

    self._create_history(hash, msg.sender, recipient)
