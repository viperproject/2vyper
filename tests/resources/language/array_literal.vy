#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

array: int128[5]


@public
def assign_field():
    self.array = [1, 2, 3, 4, 5]


@public
def assign_local():
    a: int128[5] = [2, 3, 4, 5, 6]