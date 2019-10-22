#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


struct        S :
    s: int128


contract     C        :
    def    f () : modifying


#@     invariant    :   True


#@          ensures       : True
@public
def foo():
    pass
