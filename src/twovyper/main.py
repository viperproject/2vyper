"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import argparse
import logging
import os

from time import time

from jpype import JException

from twovyper import config
from twovyper import vyper

from twovyper.parsing import parser
from twovyper.analysis import analyzer
from twovyper.translation import translator
from twovyper.translation.translator import TranslationOptions

from twovyper.viper.jvmaccess import JVM
from twovyper.viper.typedefs import Program

from twovyper.verification import error_manager

from twovyper.verification.verifier import (
    VerificationResult,
    ViperVerifier, AbstractVerifier
)

from twovyper.exceptions import (
    InvalidVyperException, ParseException, UnsupportedException, InvalidProgramException, ConsistencyException
)


class TwoVyper:

    def __init__(self, jvm: JVM, get_model: bool = False):
        self.jvm = jvm
        self.get_model = get_model

    def translate(self, path: str, vyper_root: str = None, skip_vyper: bool = False) -> Program:
        path = os.path.abspath(path)
        error_manager.clear()

        # Check that the file is a valid Vyper contract
        if not skip_vyper:
            vyper.check(path, vyper_root)

        logging.debug("Start parsing.")

        vyper_program = parser.parse(path, vyper_root)

        logging.info("Finished parsing.")
        logging.debug("Start analyzing.")

        for interface in vyper_program.interfaces.values():
            analyzer.analyze(interface)
        analyzer.analyze(vyper_program)

        logging.info("Finished analyzing.")
        logging.debug("Start translating.")

        options = TranslationOptions(self.get_model)
        translated = translator.translate(vyper_program, options, self.jvm)

        logging.info("Finished translating.")

        return translated

    def verify(self, program: Program, path: str, backend: str) -> VerificationResult:
        """
        Verifies the given Viper program
        """
        logging.debug("Start verifying.")

        verifier: AbstractVerifier = ViperVerifier[backend].value
        result = verifier.verify(program, self.jvm, path, self.get_model)

        logging.info("Finished verifying.")

        return result


def main() -> None:
    """
    Entry point for the verifier.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'vyper_file',
        help='Python file to verify'
    )
    parser.add_argument(
        '--verifier',
        help='verifier to be used (carbon or silicon)',
        choices=['silicon', 'carbon'],
        default='silicon'
    )
    parser.add_argument(
        '--viper-jar-path',
        help='Java CLASSPATH that includes Viper class files',
        default=None
    )
    parser.add_argument(
        '--z3',
        help='path to Z3 executable',
        default=config.z3_path
    )
    parser.add_argument(
        '--boogie',
        help='path to Boogie executable',
        default=config.boogie_path
    )
    parser.add_argument(
        '--counterexample',
        action='store_true',
        help='print a counterexample if the verification fails',
    )
    parser.add_argument(
        '--vyper-root',
        help='import root directory for the Vyper contract',
        default=None
    )
    parser.add_argument(
        '--skip-vyper',
        action='store_true',
        help='skip validity check of contract with the Vyper compiler'
    )
    parser.add_argument(
        '--print-viper',
        action='store_true',
        help='print generated Viper program'
    )
    parser.add_argument(
        '--write-viper-to-file',
        default=None,
        help='write generated Viper program to specified file'
    )
    parser.add_argument(
        '--log',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='log level',
        default='WARNING'
    )
    parser.add_argument(
        '--benchmark',
        type=int,
        help='run verification the given number of times to benchmark performance',
        default=-1
    )
    parser.add_argument(
        '--ide-mode',
        action='store_true',
        help='output errors in IDE format'
    )

    args = parser.parse_args()

    if args.viper_jar_path:
        config.classpath = args.viper_jar_path
    else:
        config.set_classpath(args.verifier)
    config.boogie_path = args.boogie
    config.z3_path = args.z3

    if not config.classpath:
        parser.error('missing argument: --viper-jar-path')
    if not config.z3_path:
        parser.error('missing argument: --z3')
    if args.verifier == 'carbon' and not config.boogie_path:
        parser.error('missing argument: --boogie')

    formatter = logging.Formatter()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logging.basicConfig(level=args.log, handlers=[handler])

    jvm = JVM(config.classpath)
    translate_and_verify(args.vyper_file, jvm, args)


def translate_and_verify(vyper_file, jvm, args, print=print):
    try:
        start = time()
        tw = TwoVyper(jvm, args.counterexample)
        program = tw.translate(vyper_file, args.vyper_root, args.skip_vyper)
        if args.print_viper:
            print(str(program))
        if args.write_viper_to_file:
            with open(args.write_viper_to_file, 'w') as fp:
                fp.write(str(program))

        backend = args.verifier

        if args.benchmark >= 1:
            print("Run, Total, Start, End, Time")
            for i in range(args.benchmark):
                start = time()
                prog = tw.translate(vyper_file, args.vyper_root, args.skip_vyper)
                vresult = tw.verify(prog, vyper_file, backend)
                end = time()
                print(f"{i}, {args.benchmark}, {start}, {end}, {end - start}")
        else:
            vresult = tw.verify(program, vyper_file, backend)
        print(vresult.string(args.ide_mode, include_model=args.counterexample))
        end = time()
        duration = end - start
        print(f"Verification took {duration:.2f} seconds.")
    except (InvalidProgramException, UnsupportedException) as e:
        print(e.error_string())
    except ConsistencyException as e:
        print(e.program)
        print(e.message)
        for error in e.errors:
            print(error.toString())
    except (InvalidVyperException, ParseException) as e:
        print(e.message)
    except JException as e:
        print(e.stacktrace())
        raise e


if __name__ == '__main__':
    main()
