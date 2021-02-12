#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


#@ config: allocation, no_performs, no_derived_wei_resource


#@ invariant: forall({a: address}, trusted(self, by=a))

@public
def __init__():
    #@ foreach({a: address}, trust(self, True, actor=a))
    pass
