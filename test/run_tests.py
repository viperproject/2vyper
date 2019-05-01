"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import pytest

import os
import glob

from tests import _test


def get_tests():
    test_dir = os.path.join(os.path.dirname(__file__), 'resources/')
    files = [f for f in glob.glob(test_dir + "/**/*.vy", recursive=True)]
    return files

def file_id(file):
    return os.path.basename(file)

@pytest.mark.parametrize('file', get_tests(), ids=file_id)
def test_file(file):
    _test(file)
