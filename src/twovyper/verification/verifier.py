"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import abc

from enum import Enum

from twovyper import config

from twovyper.utils import list_to_seq

from twovyper.viper.typedefs import Program
from twovyper.viper.jvmaccess import JVM

from twovyper.verification.result import VerificationResult, Success, Failure


class AbstractVerifier(abc.ABC):

    @abc.abstractmethod
    def initialize(self, jvm: JVM, file: str, get_model: bool = False):
        pass

    @abc.abstractmethod
    def verify(self, program: Program) -> VerificationResult:
        pass


class Silicon(AbstractVerifier):
    """
    Provides access to the Silicon verifier
    """

    def initialize(self, jvm: JVM, filename: str, get_model: bool = False):
        self.jvm = jvm
        self.silver = jvm.viper.silver
        if not jvm.is_known_class(jvm.viper.silicon.Silicon):
            raise Exception('Silicon backend not found on classpath.')
        self.silicon = jvm.viper.silicon.Silicon()

        args = [
            '--z3Exe', config.z3_path,
            '--disableCatchingExceptions',
            *(['--model=variables'] if get_model else []),
            filename
        ]

        self.silicon.parseCommandLine(list_to_seq(args, jvm))
        self.silicon.start()
        self.ready = True

    def verify(self, program: Program) -> VerificationResult:
        """
        Verifies the given program using Silicon
        """
        if not self.ready:
            self.silicon.restart()
        result = self.silicon.verify(program)
        self.ready = False
        if isinstance(result, self.silver.verifier.Failure):
            it = result.errors().toIterator()
            errors = []
            while it.hasNext():
                errors += [it.next()]
            return Failure(errors, self.jvm)
        else:
            return Success()

    def __del__(self):
        if hasattr(self, 'silicon') and self.silicon:
            self.silicon.stop()


class Carbon:
    """
    Provides access to the Carbon verifier
    """

    def initialize(self, jvm: JVM, filename: str, get_model: bool = False):
        self.silver = jvm.viper.silver
        if not jvm.is_known_class(jvm.viper.carbon.CarbonVerifier):
            raise Exception('Carbon backend not found on classpath.')
        if config.boogie_path is None:
            raise Exception('Boogie not found.')
        self.carbon = jvm.viper.carbon.CarbonVerifier()

        args = [
            '--boogieExe', config.boogie_path,
            '--z3Exe', config.z3_path,
            *(['--model=variables'] if get_model else []),
            filename
        ]

        self.carbon.parseCommandLine(list_to_seq(args, jvm))
        self.carbon.start()
        self.ready = True
        self.jvm = jvm

    def verify(self, program: Program) -> VerificationResult:
        """
        Verifies the given program using Carbon
        """
        if not self.ready:
            self.carbon.restart()
        result = self.carbon.verify(program)
        self.ready = False
        if isinstance(result, self.silver.verifier.Failure):
            it = result.errors().toIterator()
            errors = []
            while it.hasNext():
                errors += [it.next()]
            return Failure(errors)
        else:
            return Success()


class ViperVerifier(Enum):
    silicon = Silicon()
    carbon = Carbon()
