"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import os
import sys
import shutil

import nagini_translation.backends


def _backend_path(verifier: str):
    backends = os.path.dirname(nagini_translation.backends.__file__)
    return os.path.join(backends, f'{verifier}.jar')


def _executable_path(cmd: str) -> str:
    return shutil.which(cmd, os.X_OK)


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
    defined, then checks the OS specific directory.
    """

    boogie_exe = os.environ.get('BOOGIE_EXE')
    if boogie_exe:
        return boogie_exe

    cmd = 'Boogie.exe' if sys.platform.startswith('win') else 'boogie'
    return _executable_path(cmd)


def _get_z3_path():
    """ Tries to detect path to Z3 executable.

    First tries the environment variable ``Z3_EXE``. If it is not defined,
    then checks the z3 dependency. Otherwise, the system default is used.
    """

    z3_exe = os.environ.get('Z3_EXE')
    if z3_exe:
        return z3_exe

    cmd = 'z3.exe' if sys.platform.startswith('win') else 'z3'
    ex_path = os.path.dirname(sys.executable)
    path = os.path.join(ex_path, cmd)
    if os.path.isfile(path) and os.access(path, os.X_OK):
        return path

    return _executable_path(cmd)


def set_classpath(v: str):
    global classpath
    classpath = _construct_classpath(v)


classpath = _construct_classpath()
z3_path = _get_z3_path()
boogie_path = _get_boogie_path()
