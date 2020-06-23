#
# Copyright (c) 2020 ETH Zurich
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

# Verification took   2.43 seconds. [benchmark=10] (With assume_private_function)
# Verification took   3.53 seconds. [benchmark=10] (With inline)

#@ensures: success() ==> result() == 3
@private
@constant
def get_3() -> int128:
    return 3

#@ensures: success() ==> result() == 4
@private
@constant
def via_get_4() -> int128:
    return self.get_3() + 1

#@ensures: success() ==> result() == 5
@private
@constant
def via_via_get_5() -> int128:
    return self.via_get_4() + 1


#@ensures: success() ==> result() == 4
@private
@constant
def via_via_via_get_4() -> int128:
    return self.via_via_get_5() - 1


#@ensures: success() ==> result() == 3
@public
@constant
def via_via_via_via_get_3() -> int128:
    return self.via_via_via_get_4() - 1

#@ensures: success() ==> result() == 2
@public
@constant
def via_via_via_via_get_2() -> int128:
    return self.via_via_via_get_4() - 2
