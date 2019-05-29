"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List, Optional
from abc import ABCMeta

from nagini_translation.viper.typedefs import AbstractVerificationError
from nagini_translation.viper.jvmaccess import JVM

from nagini_translation.verification import error_manager


class VerificationResult(metaclass=ABCMeta):
    pass


class Success(VerificationResult):
    """
    Encodes a verification success
    """

    def __bool__(self):
        return True

    def to_string(self, ide_mode: bool, show_viper_errors: bool) -> str:
        return "Verification successful"


class Failure(VerificationResult):
    """
    Encodes a verification failure and provides access to the errors
    """

    def __init__(
            self, errors: List[AbstractVerificationError],
            jvm: Optional[JVM] = None):
        self.errors = error_manager.convert(errors, jvm)

    def __bool__(self):
        return False

    def to_string(self, ide_mode: bool, show_viper_errors: bool) -> str:
        errors = [error.string(ide_mode, show_viper_errors) for error in self.errors]
        return "Verification failed\nErrors:\n" + '\n'.join(errors)
