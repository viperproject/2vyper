"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from abc import ABCMeta
from typing import List, Optional

from twovyper.viper.jvmaccess import JVM
from twovyper.viper.typedefs import AbstractVerificationError

from twovyper.verification import error_manager


class VerificationResult(metaclass=ABCMeta):
    pass


class Success(VerificationResult):
    """
    Encodes a verification success
    """

    def __bool__(self):
        return True

    def string(self, ide_mode: bool, include_model: bool = False) -> str:
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

    def string(self, ide_mode: bool, include_model: bool = False) -> str:
        errors = [error.string(ide_mode, include_model) for error in self.errors]
        return "Verification failed\nErrors:\n" + '\n'.join(errors)
