#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from . import interface_with_implements

implements: interface_with_implements


@public
def foo(a: address) -> bool:
    return interface_with_implements(a).bar()


@public
def bar() -> bool:
    return True
