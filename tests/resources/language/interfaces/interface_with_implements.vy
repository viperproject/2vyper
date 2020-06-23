#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ interface


#@ ensures: success() and implements(a, interface_with_implements) ==> result() == True
@public
def foo(a: address) -> bool:
    raise "Not implemented"


#@ ensures: success() ==> result() == True
@public
def bar() -> bool:
    raise "Not implemented"