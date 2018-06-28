"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

"""Pytest plugin for further test configuration.

See http://doc.pytest.org/en/latest/writing_plugins.html for documentation.
"""
import os
import pytest

from nagini_translation.lib import config
from nagini_translation.verifier import ViperVerifier
from typing import List


_TRANSLATION_TEST_FUNCTION_NAME = 'test_translation'
_VERIFICATION_TEST_FUNCTION_NAME = 'test_verification'
_SIF_PERFORMANCE_TEST_FUNCTION_NAME = 'test_sif_performance'

_TRANSLATION_TESTS_SUFFIX = 'translation'
_VERIFICATION_TESTS_SUFFIX = 'verification'

_FUNCTIONAL_TESTS_DIR = 'tests/functional/'
_SIF_TESTS_DIR = 'tests/sif/'
_IO_TESTS_DIR = 'tests/io/'
_OBLIGATIONS_TESTS_DIR = 'tests/obligations/'


class PyTestConfig:
    """Class that holds the configuration for tests."""
    def __init__(self):
        self.translation_test_dirs = []
        self.verification_test_dirs = []
        self.single_test = None
        self.verifiers = []
        self.sif_performance = None
        
        self.init_from_config_file()

    def init_from_config_file(self):
        test_config = config.test_config

        for test in test_config.tests:
            self.add_test(test)

        for verifier in test_config.verifiers:
            self.add_verifier(verifier)

    def add_test(self, test: str):
        if test == 'functional':
            self._add_test_dir(_FUNCTIONAL_TESTS_DIR)
        elif test == 'sif':
            self._add_test_dir(_SIF_TESTS_DIR)
        elif test == 'io':
            self._add_test_dir(_IO_TESTS_DIR)
        elif test == 'obligations':
            self._add_test_dir(_OBLIGATIONS_TESTS_DIR)
        else:
            print('Unrecognized test set.')

    def _add_test_dir(self, path: str):
        self.translation_test_dirs.append(os.path.join(
            path, _TRANSLATION_TESTS_SUFFIX))
        self.verification_test_dirs.append(os.path.join(
            path, _VERIFICATION_TESTS_SUFFIX))

    def clear_tests(self):
        self.translation_test_dirs = []
        self.verification_test_dirs = []

    def add_verifier(self, verifier: str):
        if verifier == 'silicon':
            self.verifiers.append(ViperVerifier.silicon)
        elif verifier == 'carbon':
            self.verifiers.append(ViperVerifier.carbon)
        else:
            print('Unrecognized verifier.')

    def clear_verifiers(self):
        self.verifiers = []

_pytest_config = PyTestConfig()


def _test_files(test_dir: str) -> List[str]:
    result = []
    for root, dir_names, file_names in os.walk(test_dir, topdown=True):
        if 'tests' in file_names:
            # tests file lists all tests in this directory, so we read
            # its contents and do not proceed deeper.
            with open(os.path.join(root, 'tests')) as fp:
                for file_name in fp:
                    result.append(os.path.join(root, file_name.strip()))
            dir_names.clear()
            continue
        if 'resources' in dir_names:
            # Skip resources directory.
            dir_names.remove('resources')
        for file_name in file_names:
            if file_name.endswith('.py'):
                result.append(os.path.join(root, file_name))
    result = [path for path in sorted(result)
              if path not in config.test_config.ignore_tests]
    return result


def pytest_addoption(parser: 'pytest.config.Parser'):
    """Command line options for the test runner."""
    # Preferably, we could specify the tests and verifiers as a list, but
    # unfortunately, pytest_parser.addoption does not play well with
    # action='append'.
    parser.addoption('--single-test', dest='single_test', action='store', default=None)
    parser.addoption('--all-tests', dest='all_tests', action='store_true')
    parser.addoption('--functional', dest='functional', action='store_true')
    parser.addoption('--sif', dest='sif', action='store_true')
    parser.addoption('--io', dest='io', action='store_true')
    parser.addoption('--obligations', dest='obligations', action='store_true')
    parser.addoption('--all-verifiers', dest='all_verifiers',
                     action='store_true')
    parser.addoption('--silicon', dest='silicon', action='store_true')
    parser.addoption('--carbon', dest='carbon', action='store_true')
    parser.addoption('--sif-performance', dest='sif_performance', action='store', default=None)


def pytest_configure(config: 'pytest.config.Config'):
    """Adds command line arguments to the PyTestConfig object."""
    # Setup tests.
    tests = []
    if config.option.all_tests:
        tests = ['functional', 'sif', 'io', 'obligations']
    else:
        if config.option.functional:
            tests.append('functional')
        if config.option.sif:
            tests.append('sif')
        if config.option.io:
            tests.append('io')
        if config.option.obligations:
            tests.append('obligations')
    if config.option.sif_performance:
        tests = ['functional']
        _pytest_config.sif_performance = config.option.sif_performance
    if tests:
        # Overwrite config file options.
        _pytest_config.clear_tests()
        for test in tests:
            _pytest_config.add_test(test)
    elif config.option.single_test:
        _pytest_config.clear_tests()
        _pytest_config.single_test = config.option.single_test
    if not _pytest_config.translation_test_dirs and not _pytest_config.single_test:
        pytest.exit('No test sets specified.')
    # Setup verifiers.
    verifiers = []
    if config.option.all_verifiers:
        verifiers = ['silicon', 'carbon']
    else:
        if config.option.silicon:
            verifiers.append('silicon')
        if config.option.carbon:
            verifiers.append('carbon')
    if verifiers:
        # Overwrite config file options.
        _pytest_config.clear_verifiers()
        for verifier in verifiers:
            _pytest_config.add_verifier(verifier)
    if not _pytest_config.verifiers:
        pytest.exit('No verifiers specified.')


def pytest_generate_tests(metafunc: 'pytest.python.Metafunc'):
    """Parametrizes test functions based on the config."""
    func_name = metafunc.function.__name__
    test_files = []
    reload_triggers = set()
    params = []
    if func_name == _TRANSLATION_TEST_FUNCTION_NAME:
        if not _pytest_config.sif_performance:
            for test_dir in _pytest_config.translation_test_dirs:
                files = _test_files(test_dir)
                test_files.extend(files)
                reload_triggers.add(files[0])
            if _pytest_config.single_test and 'translation' in _pytest_config.single_test:
                test_files.append(_pytest_config.single_test)
            for file in test_files:
                sif = 'sif' in file
                reload_resources = file in reload_triggers
                params.append((file, sif, reload_resources))
        metafunc.parametrize('path,sif,reload_resources', params)
    elif func_name == _VERIFICATION_TEST_FUNCTION_NAME:
        if not _pytest_config.sif_performance:
            for test_dir in _pytest_config.verification_test_dirs:
                files = _test_files(test_dir)
                test_files.extend(files)
                reload_triggers.add(files[0])
            if _pytest_config.single_test and 'verification' in _pytest_config.single_test:
                test_files.append(_pytest_config.single_test)
            for file in test_files:
                sif = 'sif' in file
                reload_resources = file in reload_triggers
                params.extend([(file, verifier, sif, reload_resources) for verifier
                               in _pytest_config.verifiers])
        metafunc.parametrize('path,verifier,sif,reload_resources', params)
    elif func_name == _SIF_PERFORMANCE_TEST_FUNCTION_NAME:
        if _pytest_config.sif_performance:
            for test_dir in _pytest_config.verification_test_dirs:
                files = _test_files(test_dir)
                test_files.extend(files)
                reload_triggers.add(files[0])
            for file in test_files:
                reload_resources = file in reload_triggers
                params.extend([(file, verifier, reload_resources, _pytest_config.sif_performance)
                            for verifier in _pytest_config.verifiers])
            # set up the log file
            write_sif_performance_log_file('w', name='File', verifier='Verifier',
                                           trans_time='Translation', std_time='Std Time',
                                           sif_trans_time='SIF Translation',
                                           mpp_time='MPP Trafo', sif_time='SIF Time',
                                           passed='Result')
        metafunc.parametrize('path, verifier, reload_resources, log_file', params)
    else:
        pytest.exit('Unrecognized test function.')


def write_sif_performance_log_file(mode, name, verifier, trans_time, sif_trans_time,
                                   std_time, mpp_time, sif_time, passed):
    """Write a formatted line to the log file"""
    with open(_pytest_config.sif_performance, mode) as lf:
        name_w = 40
        number_w = 15
        if mode == 'a': # after first line, format last three as numbers
            lf.write('{:{name_width}} | {:{width}} | {:{width}f} | {:{width}f} | {:{width}f} | '
                     '{:{width}f} | {:{width}f} | {:{width}}\n'.format(
                         name, verifier, trans_time, std_time, sif_trans_time, mpp_time, sif_time,
                         passed, name_width=name_w, width=number_w))
        else:
            lf.write('{:{name_width}} | {:{width}} | {:{width}} | {:{width}} | {:{width}} | '
                     '{:{width}} | {:{width}} | {:{width}}\n'.format(
                         name, verifier, trans_time, std_time, sif_trans_time, mpp_time, sif_time,
                         passed, name_width=name_w, width=number_w))
