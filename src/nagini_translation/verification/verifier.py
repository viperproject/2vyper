"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from enum import Enum

from nagini_translation import config
from nagini_translation.viper.typedefs import Program
from nagini_translation.viper.jvmaccess import JVM

from nagini_translation.verification.result import VerificationResult, Success, Failure


class ViperVerifier(Enum):
    silicon = 'silicon'
    carbon = 'carbon'


class Silicon:
    """
    Provides access to the Silicon verifier
    """

    def __init__(self, jvm: JVM, filename: str):
        self.jvm = jvm
        self.silver = jvm.viper.silver
        if not jvm.is_known_class(jvm.viper.silicon.Silicon):
            raise Exception('Silicon backend not found on classpath.')
        self.silicon = jvm.viper.silicon.Silicon()
        args = jvm.scala.collection.mutable.ArraySeq(4)
        args.update(0, '--z3Exe')
        args.update(1, config.z3_path)
        args.update(2, '--disableCatchingExceptions')
        args.update(3, filename)
        self.silicon.parseCommandLine(args)
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

    def __init__(self, jvm: JVM, filename: str):
        self.silver = jvm.viper.silver
        if not jvm.is_known_class(jvm.viper.carbon.CarbonVerifier):
            raise Exception('Carbon backend not found on classpath.')
        if config.boogie_path is None:
            raise Exception('Boogie not found.')
        self.carbon = jvm.viper.carbon.CarbonVerifier()
        args = jvm.scala.collection.mutable.ArraySeq(5)
        args.update(0, '--boogieExe')
        args.update(1, config.boogie_path)
        args.update(2, '--z3Exe')
        args.update(3, config.z3_path)
        args.update(4, filename)
        self.carbon.parseCommandLine(args)
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
