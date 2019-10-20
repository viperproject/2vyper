"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
import os
from subprocess import Popen, PIPE

from twovyper.exceptions import InvalidVyperException


def check(file: str, root=None):
    """
    Checks that the file is a valid Vyper contract. If not, throws an `InvalidVyperException`.
    """
    if root is not None:
        cmd = os.path.join(root, 'vyper')
    else:
        cmd = 'vyper'
    pipes = Popen([cmd, file], stdout=PIPE, stderr=PIPE)
    _, stderr = pipes.communicate()

    if pipes.returncode != 0:
        err_msg = stderr.strip().decode('utf-8')
        raise InvalidVyperException(err_msg)
