#
# Copyright (c) 2019 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


@public
def split(b: bool) -> int128:
    if b:
        a: int128 = 5
        return a + 1
    else:
        a: int128[5] = [0, 0, 0, 0, 1]
        return a[4]


#@ ensures: success() ==> result() == 55
@public
def loops() -> int128:
    res: int128 = 0
    for i in range(5):
        res += i
    
    for i in range(10):
        res += i
    
    return res


#@ ensures: success() ==> result() == 20
@public
def array_loops() -> int128:
    arr1: int128[5] = [1, 2, 3, 4, 5]
    arr2: bool[5] = [True, True, True, True, True]

    res: int128 = 0
    for i in arr1:
        res += i
    
    for i in arr2:
        res += convert(i, int128)
    
    return res
