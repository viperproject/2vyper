"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import os


def viper_all():
    resource_path = os.path.join(os.path.dirname(__file__), 'all.vpr')
    with open(resource_path, 'r') as resource_file:
        return resource_file.read(), resource_path
