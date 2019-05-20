"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import os
import sys

import nagini_translation.backends


def _backend_path(verifier: str):
    backends = os.path.dirname(nagini_translation.backends.__file__)
    return os.path.join(backends, f'{verifier}.jar')


def _construct_classpath(verifier: str = 'silicon'):
    """ Contstructs JAVA classpath.

    First tries environment variables ``VIPERJAVAPATH``, ``SILICONJAR``
    and ``CARBONJAR``. If they are undefined, then uses packaged backends.
    """

    viper_java_path = os.environ.get('VIPERJAVAPATH')
    silicon_jar = os.environ.get('SILICONJAR')
    carbon_jar = os.environ.get('CARBONJAR')

    if viper_java_path:
        return viper_java_path

    if carbon_jar and verifier == 'carbon':
        return carbon_jar

    if silicon_jar and verifier == 'silicon':
        return silicon_jar

    return _backend_path(verifier)


def _get_boogie_path():
    """ Tries to detect path to Boogie executable.

    First tries the environment variable ``BOOGIE_EXE``. If it is not
    defined, then checks the OS specific directory. On Ubuntu returns a
    path only if it also finds a mono installation.
    """

    boogie_exe = os.environ.get('BOOGIE_EXE')
    if boogie_exe:
        return boogie_exe

    if sys.platform.startswith('linux'):
        if (os.path.exists('/usr/bin/boogie') and os.path.exists('/usr/bin/mono')):
            return '/usr/bin/boogie'

    return None


def _get_z3_path():
    """ Tries to detect path to Z3 executable.

    First tries the environment variable ``Z3_EXE``. If it is not
    defined, then checks the OS specific directories.
    """

    z3_exe = os.environ.get('Z3_EXE')
    if z3_exe:
        return z3_exe

    ex_path = os.path.dirname(sys.executable)
    path = os.path.join(ex_path, 'z3.exe' if sys.platform.startswith('win') else 'z3')
    if os.path.exists(path):
        return path

    return None


def set_classpath(v: str):
    global classpath
    classpath = _construct_classpath(v)


"""
JAVA class path. Initialized by calling
:py:func:`_construct_classpath`.
"""
classpath = None


"""
Path to Boogie executable. Initialized by calling
:py:func:`_get_boogie_path`.
"""
boogie_path = _get_boogie_path()


"""
Path to Z3 executable. Initialized by calling :py:func:`_get_z3_path`.
"""
z3_path = _get_z3_path()
