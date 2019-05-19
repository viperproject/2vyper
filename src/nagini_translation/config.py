"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import configparser
import glob
import os
import sys

import nagini_translation.resources


class SectionConfig:
    """A base class for configuration sections."""

    def __init__(self, config, section_name) -> None:
        self.config = config
        if section_name not in self.config:
            self.config[section_name] = {}
        self._info = self.config[section_name]


class TestConfig(SectionConfig):
    """Testing configuration."""

    def __init__(self, config) -> None:
        super().__init__(config, 'Tests')

        ignore_tests_value = self._info.get('ignore_tests')
        if not ignore_tests_value:
            self.ignore_tests = set([])
        else:
            patterns = ignore_tests_value.strip().splitlines()
            self.ignore_tests = set([i for pattern in patterns for i in glob.glob(pattern)])

        verifiers_value = self._info.get('verifiers')
        if not verifiers_value:
            self.verifiers = []
        else:
            self.verifiers = verifiers_value.strip().split()

        tests_value = self._info.get('tests')
        if not tests_value:
            self.tests = []
        else:
            self.tests = tests_value.strip().split()


class FileConfig:
    """Configuration stored in the config file."""

    def __init__(self, config_file) -> None:
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        self.test_config = TestConfig(self.config)


def resources_folder():
    resources = os.path.dirname(nagini_translation.resources.__file__)
    return resources


def _construct_classpath(verifier: str = None):
    """ Contstructs JAVA classpath.

    First tries environment variables ``VIPERJAVAPATH``, ``SILICONJAR``
    and ``CARBONJAR``. If they are undefined, then tries to use OS
    specific locations.
    """

    viper_java_path = os.environ.get('VIPERJAVAPATH')
    silicon_jar = os.environ.get('SILICONJAR')
    carbon_jar = os.environ.get('CARBONJAR')
    arpplugin_jar = os.environ.get('ARPPLUGINJAR')

    if viper_java_path:
        return viper_java_path

    if silicon_jar or carbon_jar:
        return os.pathsep.join(
            jar for jar, v in ((silicon_jar, 'carbon'),
                               (carbon_jar, 'silicon'),
                               (arpplugin_jar, 'arpplugin'))
            if jar and v != verifier)

    if sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
        if os.path.isdir('/usr/lib/viper'):
            # Check if we have Viper installed via package manager.
            return os.pathsep.join(glob.glob('/usr/lib/viper/*.jar'))

        if os.path.isdir('/usr/local/Viper/backends'):
            return os.pathsep.join(glob.glob('/usr/local/Viper/backends/*.jar'))

    resources = resources_folder()
    silicon = os.path.join(resources, 'backends', 'silicon.jar')
    carbon = os.path.join(resources, 'backends', 'carbon.jar')
    return os.pathsep.join(
        jar for jar, v in ((silicon, 'carbon'),
                           (carbon, 'silicon'),
                           (arpplugin_jar, 'arpplugin'))
        if jar and v != verifier)


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


def _get_z3_path():
    """ Tries to detect path to Z3 executable.

    First tries the environment variable ``Z3_EXE``. If it is not
    defined, then checks the OS specific directories.
    """

    z3_exe = os.environ.get('Z3_EXE')
    if z3_exe:
        return z3_exe

    if sys.platform.startswith('linux'):
        if os.path.exists('/usr/bin/viper-z3'):
            # First check if we have Z3 installed together with Viper.
            return '/usr/bin/viper-z3'
        if os.path.exists('/usr/bin/z3'):
            return '/usr/bin/z3'

    path = os.path.join(os.path.dirname(sys.executable),
                        'z3.exe' if sys.platform.startswith('win') else 'z3')
    if os.path.exists(path):
        return path


def set_verifier(v: str):
    global classpath
    not_set_by_arg = classpath == _construct_classpath()
    if not_set_by_arg:
        classpath = _construct_classpath(v)


classpath = _construct_classpath()
"""
JAVA class path. Initialized by calling
:py:func:`_construct_classpath`.
"""


boogie_path = _get_boogie_path()
"""
Path to Boogie executable. Initialized by calling
:py:func:`_get_boogie_path`.
"""


z3_path = _get_z3_path()
"""
Path to Z3 executable. Initialized by calling :py:func:`_get_z3_path`.
"""


file_config = FileConfig('nagini.cfg')
"""
Configuration read from ``nagini.cfg`` file.
"""


test_config = file_config.test_config
"""
Test configuration.
"""
