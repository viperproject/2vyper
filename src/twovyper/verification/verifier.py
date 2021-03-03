"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import abc
import logging

from enum import Enum
from typing import Optional, Any

from jpype import JPackage

from twovyper import config

from twovyper.utils import list_to_seq

from twovyper.viper.typedefs import Program
from twovyper.viper.jvmaccess import JVM

from twovyper.verification.result import VerificationResult, Success, Failure


class AbstractVerifier(abc.ABC):

    def __init__(self):
        self.jvm: Optional[JVM] = None
        self.silver: Optional[JPackage] = None

    @abc.abstractmethod
    def _initialize(self, jvm: JVM, file: str, get_model: bool = False):
        pass

    @abc.abstractmethod
    def verify(self, program: Program, jvm: JVM, filename: str, get_model: bool = False) -> VerificationResult:
        pass


class Silicon(AbstractVerifier):
    """
    Provides access to the Silicon verifier
    """

    def __init__(self):
        super().__init__()
        self.silicon: Optional[Any] = None

    def _initialize(self, jvm: JVM, filename: str, get_model: bool = False):
        self.jvm = jvm
        self.silver = jvm.viper.silver
        if not jvm.is_known_class(jvm.viper.silicon.Silicon):
            raise Exception('Silicon backend not found on classpath.')
        self.silicon = jvm.viper.silicon.Silicon()

        args = [
            '--z3Exe', config.z3_path,
            '--disableCatchingExceptions',
            *(['--counterexample=native'] if get_model else []),
            filename
        ]

        self.silicon.parseCommandLine(list_to_seq(args, jvm))
        self.silicon.start()

        logging.info("Initialized Silicon.")

    def verify(self, program: Program, jvm: JVM, filename: str, get_model: bool = False) -> VerificationResult:
        """
        Verifies the given program using Silicon
        """
        if self.silicon is None:
            self._initialize(jvm, filename, get_model)
            assert self.silicon is not None
        result = self.silicon.verify(program)
        if isinstance(result, self.silver.verifier.Failure):
            logging.info("Silicon returned with: Failure.")
            it = result.errors().toIterator()
            errors = []
            while it.hasNext():
                errors += [it.next()]
            return Failure(errors, self.jvm)
        else:
            logging.info("Silicon returned with: Success.")
            return Success()

    def __del__(self):
        if self.silicon is not None:
            self.silicon.stop()


class Carbon(AbstractVerifier):
    """
    Provides access to the Carbon verifier
    """

    def __init__(self):
        super().__init__()
        self.carbon: Optional[Any] = None

    def _initialize(self, jvm: JVM, filename: str, get_model: bool = False):
        self.silver = jvm.viper.silver
        if not jvm.is_known_class(jvm.viper.carbon.CarbonVerifier):
            raise Exception('Carbon backend not found on classpath.')
        if config.boogie_path is None:
            raise Exception('Boogie not found.')
        self.carbon = jvm.viper.carbon.CarbonVerifier()

        args = [
            '--boogieExe', config.boogie_path,
            '--z3Exe', config.z3_path,
            *(['--counterexample=variables'] if get_model else []),
            filename
        ]

        self.carbon.parseCommandLine(list_to_seq(args, jvm))
        self.carbon.start()
        self.jvm = jvm

        logging.info("Initialized Carbon.")

    def verify(self, program: Program, jvm: JVM, filename: str, get_model: bool = False) -> VerificationResult:
        """
        Verifies the given program using Carbon
        """
        if self.carbon is None:
            self._initialize(jvm, filename, get_model)
            assert self.carbon is not None
        result = self.carbon.verify(program)
        if isinstance(result, self.silver.verifier.Failure):
            logging.info("Carbon returned with: Failure.")
            it = result.errors().toIterator()
            errors = []
            while it.hasNext():
                errors += [it.next()]
            return Failure(errors)
        else:
            logging.info("Carbon returned with: Success.")
            return Success()

    def __del__(self):
        if self.carbon is not None:
            self.carbon.stop()


class ViperVerifier(Enum):
    silicon = Silicon()
    carbon = Carbon()
