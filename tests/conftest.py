"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""


option = None


def pytest_addoption(parser):
    parser.addoption('--verifier', action='store', default='silicon')
    parser.addoption('--model', action='store_true', default=False)
    parser.addoption('--check-ast-inconsistencies', action='store_true', default=False)
    parser.addoption('--store-viper', dest='store_viper', action='store_true')


def pytest_configure(config):
    global option
    option = config.option
