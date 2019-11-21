"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import pytest

import os
import glob

from conftest import option
from tests import _init_jvm, _init_model, _test


def setup_module(module):
    _init_jvm(option.verifier)
    _init_model(option.model)


def get_tests():
    test_dir = os.path.join(os.path.dirname(__file__), 'resources/')
    files = [f for f in glob.glob(test_dir + "/**/*.vy", recursive=True)]
    return sorted(files, key=str.casefold)


def file_id(file):
    return os.path.basename(file)


@pytest.mark.parametrize('file', get_tests(), ids=file_id)
def test_file(file):
    _test(file)
