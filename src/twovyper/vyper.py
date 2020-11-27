"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import logging
import os
import re
from subprocess import Popen, PIPE
from typing import Optional, List, Dict

import vvm
import vyper
from semantic_version import NpmSpec, Version
from vvm.utils.convert import to_vyper_version

from twovyper.exceptions import InvalidVyperException, UnsupportedVersionException

try:
    # noinspection PyUnresolvedReferences,PyUnboundLocalVariable
    imported
except NameError:
    imported = True  # means the module is being imported
else:
    imported = False  # means the module is being reloaded

if imported:
    original_get_executable = vvm.install.get_executable

    def get_executable(version=None, vvm_binary_path=None) -> str:
        path = original_get_executable(version, vvm_binary_path)
        return os.path.abspath(path)

    vvm.install.get_executable = get_executable

version_pragma_pattern = re.compile(r"(?:\n|^)\s*#\s*@version\s*([^\n]*)")
comment_pattern = re.compile(r"(?:\n|^)\s*(#|$)")

VYPER_VERSION = to_vyper_version(vyper.__version__)
INSTALLED_VYPER_VERSIONS: Optional[List[Version]] = None
AVAILABLE_VYPER_VERSIONS: Optional[List[Version]] = None

# noinspection PyUnboundLocalVariable
_current_vyper_version: Optional[Version] = None if imported else _current_vyper_version


def get_vyper_version() -> Version:
    if _current_vyper_version is None:
        return VYPER_VERSION
    return _current_vyper_version


def _parse_version_string(version_str: str) -> NpmSpec:
    try:
        return NpmSpec(version_str)
    except ValueError:
        try:
            version = to_vyper_version(version_str)
            return NpmSpec(str(version))
        except Exception:
            raise InvalidVyperException(f"Cannot parse Vyper version from pragma: {version_str}")


def _get_vyper_pragma_spec(path: str) -> NpmSpec:
    pragma_string = None
    with open(path, 'r') as file:
        for line in file:
            pragma_match = version_pragma_pattern.match(line)
            if pragma_match is not None:
                pragma_string = pragma_match.groups()[0]
                pragma_string = " ".join(pragma_string.split())
                break
            comment_match = comment_pattern.match(line)
            if comment_match is None:
                # version pragma has to comme before code
                break

    if pragma_string is None:
        pragma_string = vyper.__version__
        logging.warning(f'No version pragma found. (Using vyper version "{pragma_string}" instead.)')

    return _parse_version_string(pragma_string)


def _find_vyper_version(file: str) -> str:
    global INSTALLED_VYPER_VERSIONS
    if INSTALLED_VYPER_VERSIONS is None:
        INSTALLED_VYPER_VERSIONS = vvm.get_installed_vyper_versions()
        INSTALLED_VYPER_VERSIONS.append(VYPER_VERSION)

    pragma_specs = _get_vyper_pragma_spec(file)
    version = pragma_specs.select(INSTALLED_VYPER_VERSIONS)

    if not version:
        global AVAILABLE_VYPER_VERSIONS
        if AVAILABLE_VYPER_VERSIONS is None:
            AVAILABLE_VYPER_VERSIONS = vvm.get_installable_vyper_versions()
        version = pragma_specs.select(AVAILABLE_VYPER_VERSIONS)
        if not version:
            raise InvalidVyperException(f"Invalid vyper version pragma: {pragma_specs}")
        lock = vvm.install.get_process_lock(f"locked${version}")
        with lock:
            try:
                get_executable(version)
            except vvm.exceptions.VyperNotInstalled:
                vvm.install_vyper(version)
            if version not in INSTALLED_VYPER_VERSIONS:
                INSTALLED_VYPER_VERSIONS.append(version)

    return version


def check(file: str, root=None):
    """
    Checks that the file is a valid Vyper contract. If not, throws an `InvalidVyperException`.
    """

    if VYPER_VERSION == _current_vyper_version:
        path_str = 'vyper'
    else:
        path = get_executable(_current_vyper_version)
        path_str = os.path.abspath(path)

    pipes = Popen([path_str, file], stdout=PIPE, stderr=PIPE, cwd=root)
    _, stderr = pipes.communicate()

    if pipes.returncode != 0:
        err_msg = stderr.strip().decode('utf-8')
        raise InvalidVyperException(err_msg)


def set_vyper_version(file: str):
    global _current_vyper_version
    _current_vyper_version = _find_vyper_version(file)


def select_version(value_dict: Dict[str, object], default: object = None) -> object:
    vyper_version = get_vyper_version()
    for version_str, value in value_dict.items():
        specs = _parse_version_string(version_str)
        if specs.match(vyper_version):
            return value
    else:
        if default is None:
            raise UnsupportedVersionException()
        return default
