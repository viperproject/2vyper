"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import os
import sys
import shutil

import twovyper.backends


def _backend_path(verifier: str):
    backends = os.path.dirname(twovyper.backends.__file__)
    return os.path.join(backends, f'{verifier}.jar')


def _sif_path():
    backends = os.path.dirname(twovyper.backends.__file__)
    return os.path.join(backends, 'silver-sif-extension.jar')


def _executable_path(cmd: str, env: str = None) -> str:
    if env:
        env_var = os.environ.get(env)
        if env_var:
            return env_var

    return shutil.which(cmd, os.X_OK)


def _construct_classpath(verifier: str = 'silicon'):
    """ Contstructs JAVA classpath.

    First tries environment variables ``VIPERJAVAPATH``, ``SILICONJAR``
    and ``CARBONJAR``. If they are undefined, then uses packaged backends.
    """

    viper_java_path = os.environ.get('VIPERJAVAPATH')
    silicon_jar = os.environ.get('SILICONJAR')
    carbon_jar = os.environ.get('CARBONJAR')
    sif_jar = os.environ.get('SIFJAR')

    if viper_java_path:
        return viper_java_path

    if silicon_jar and verifier == 'silicon':
        verifier_path = silicon_jar
    elif carbon_jar and verifier == 'carbon':
        verifier_path = carbon_jar
    else:
        verifier_path = _backend_path(verifier)

    sif_path = sif_jar or _sif_path()

    return os.pathsep.join([verifier_path, sif_path])


def _get_boogie_path():
    """ Tries to detect path to Boogie executable.

    First tries the environment variable ``BOOGIE_EXE``. If it is not
    defined, it uses the system default.
    """

    cmd = 'Boogie.exe' if sys.platform.startswith('win') else 'boogie'
    return _executable_path(cmd, 'BOOGIE_EXE')


def _get_z3_path():
    """ Tries to detect path to Z3 executable.

    First tries the environment variable ``Z3_EXE``. If it is not defined,
    it uses the system default (which is probably the one installed by the dependency).
    """

    cmd = 'z3.exe' if sys.platform.startswith('win') else 'z3'
    return _executable_path(cmd, 'Z3_EXE')


def set_classpath(v: str):
    global classpath
    classpath = _construct_classpath(v)


classpath = _construct_classpath()
z3_path = _get_z3_path()
boogie_path = _get_boogie_path()
