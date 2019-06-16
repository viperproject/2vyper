#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

#@ requires: start > 0
#@ ensures: result() == (99 * 100) / 2 + 100 * start
@public
def sum_of_numbers(start: int128) -> int128:
    sum: int128
    for i in range(start, start + 100):
        sum += i

    return sum
