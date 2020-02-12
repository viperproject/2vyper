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
from tests import _init_jvm, _init_model, _init_store_viper, _test


def setup_module(module):
    _init_jvm(option.verifier)
    _init_model(option.model)
    _init_store_viper(option.store_viper)


def get_tests():
    test_dir = 'tests/resources/'
    files = [f for f in glob.glob(test_dir + "/**/*.vy", recursive=True)]
    return sorted(files, key=str.casefold)


def file_id(file):
    return os.path.basename(file)


@pytest.mark.parametrize('file', get_tests(), ids=file_id)
def test_file(file):
    _test(file)
