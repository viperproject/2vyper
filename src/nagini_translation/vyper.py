"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from subprocess import check_call, DEVNULL, CalledProcessError

from nagini_translation.errors.translation import InvalidVyperException


def check(file: str):
    try:
        check_call(['vyper', file], stdout=DEVNULL, stderr=DEVNULL)
    except CalledProcessError:
        raise InvalidVyperException()
