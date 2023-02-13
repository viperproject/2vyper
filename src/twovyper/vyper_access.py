"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import logging
import os
import re
from subprocess import Popen, PIPE
from typing import Optional, List, Dict, TypeVar

import vvm
import vyper
from semantic_version import NpmSpec, Version
from vvm.utils.convert import to_vyper_version

from twovyper.exceptions import InvalidVyperException, UnsupportedVersionException

try:
    # noinspection PyUnresolvedReferences,PyUnboundLocalVariable
    _imported
except NameError:
    _imported = True  # means the module is being imported
else:
    _imported = False  # means the module is being reloaded

if _imported:
    _original_get_executable = vvm.install.get_executable

    def _get_executable(version=None, vvm_binary_path=None) -> str:
        path = _original_get_executable(version, vvm_binary_path)
        return os.path.abspath(path)

    _version_pragma_pattern = re.compile(r"(?:\n|^)\s*#\s*@version\s*([^\n]*)")
    _comment_pattern = re.compile(r"(?:\n|^)\s*(#|$)")

    _VYPER_VERSION = to_vyper_version(vyper.__version__)
    _installed_vyper_versions: Optional[List[Version]] = None
    _available_vyper_versions: Optional[List[Version]] = None

    _current_vyper_version: Optional[Version] = None

    _cache_of_parsed_version_strings: Dict[str, NpmSpec] = {}

# noinspection PyUnboundLocalVariable
vvm.install.get_executable = _get_executable


def _parse_version_string(version_str: str) -> NpmSpec:
    result = _cache_of_parsed_version_strings.get(version_str)
    if result is not None:
        return result
    try:
        result = NpmSpec(version_str)
    except ValueError:
        try:
            version = to_vyper_version(version_str)
            result = NpmSpec(str(version))
        except Exception:
            raise InvalidVyperException(f"Cannot parse Vyper version from pragma: {version_str}")
    _cache_of_parsed_version_strings[version_str] = result
    return result


def _get_vyper_pragma_spec(path: str) -> NpmSpec:
    pragma_string = None
    with open(path, 'r') as file:
        for line in file:
            pragma_match = _version_pragma_pattern.match(line)
            if pragma_match is not None:
                pragma_string = pragma_match.groups()[0]
                pragma_string = " ".join(pragma_string.split())
                break
            comment_match = _comment_pattern.match(line)
            if comment_match is None:
                # version pragma has to comme before code
                break

    if pragma_string is None:
        pragma_string = vyper.__version__
        logging.warning(f'No version pragma found. (Using vyper version "{pragma_string}" instead.)')

    return _parse_version_string(pragma_string)


def _find_vyper_version(file: str) -> str:
    global _installed_vyper_versions
    if _installed_vyper_versions is None:
        _installed_vyper_versions = vvm.get_installed_vyper_versions()
        _installed_vyper_versions.append(_VYPER_VERSION)

    pragma_specs = _get_vyper_pragma_spec(file)
    version = pragma_specs.select(_installed_vyper_versions)

    if not version:
        global _available_vyper_versions
        if _available_vyper_versions is None:
            _available_vyper_versions = vvm.get_installable_vyper_versions()
        version = pragma_specs.select(_available_vyper_versions)
        if not version:
            raise InvalidVyperException(f"Invalid vyper version pragma: {pragma_specs}")
        lock = vvm.install.get_process_lock(f"locked${version}")
        with lock:
            try:
                _get_executable(version)
            except vvm.exceptions.VyperNotInstalled:
                vvm.install_vyper(version)
            if version not in _installed_vyper_versions:
                _installed_vyper_versions.append(version)

    return version


def check(file: str, root=None):
    """
    Checks that the file is a valid Vyper contract. If not, throws an `InvalidVyperException`.
    """

    if _VYPER_VERSION == _current_vyper_version:
        path_str = 'vyper'
    else:
        path = _get_executable(_current_vyper_version)
        path_str = os.path.abspath(path)

    pipes = Popen([path_str, file], stdout=PIPE, stderr=PIPE, cwd=root)
    _, stderr = pipes.communicate()

    if pipes.returncode != 0:
        err_msg = stderr.strip().decode('utf-8')
        raise InvalidVyperException(err_msg)


def get_vyper_version() -> Version:
    if _current_vyper_version is None:
        return _VYPER_VERSION
    return _current_vyper_version


def set_vyper_version(file: str):
    global _current_vyper_version
    _current_vyper_version = _find_vyper_version(file)


def is_compatible_version(version: str) -> bool:
    vyper_version = get_vyper_version()
    specs = _parse_version_string(version)
    return specs.match(vyper_version)


T = TypeVar('T')


def select_version(value_dict: Dict[str, T], default: T = None) -> T:
    for version_str, value in value_dict.items():
        if is_compatible_version(version_str):
            return value
    else:
        if default is None:
            raise UnsupportedVersionException()
        return default
