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
    ViperVerifier
)

from twovyper.exceptions import (
    InvalidVyperException, UnsupportedException, InvalidProgramException, ConsistencyException
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

        vyper_program = parser.parse(path, vyper_root)
        for interface in vyper_program.interfaces.values():
            analyzer.analyze(interface)
        analyzer.analyze(vyper_program)

        options = TranslationOptions(self.get_model)
        return translator.translate(vyper_program, options, self.jvm)

    def verify(self, program: Program, path: str, backend: str) -> VerificationResult:
        """
        Verifies the given Viper program
        """
        verifier = ViperVerifier[backend].value
        verifier.initialize(self.jvm, path, self.get_model)
        return verifier.verify(program)


def _parse_log_level(log_level_string: str) -> int:
    """ Parses the log level provided by the user.
    """
    LOG_LEVELS = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']

    log_level_string_upper = log_level_string.upper()
    if log_level_string_upper in LOG_LEVELS:
        return getattr(logging, log_level_string_upper, logging.WARNING)
    else:
        msg = f'Invalid logging level {log_level_string} (expected one of: {LOG_LEVELS})'
        raise argparse.ArgumentTypeError(msg)


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
        '--model',
        action='store_true',
        help='print a counterexample if the verification fails',
    )
    parser.add_argument(
        '--vyper-root',
        help='import root directory for the Vyper compiler',
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
        '--show-viper-errors',
        action='store_true',
        help='show Viper-level error messages if no Python errors are available'
    )
    parser.add_argument(
        '--log',
        type=_parse_log_level,
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
        help='Output errors in IDE format'
    )
    parser.add_argument(
        '--start-server',
        action='store_true',
        help='Start 2Vyper server'
    )
    parser.add_argument(
        '--jvm-path',
        help='Path to LibJVM',
        default=None
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

    logging.basicConfig(level=args.log)

    jvm = JVM(config.classpath, args.jvm_path)
    if args.start_server:
        import zmq
        from twovyper.client import DEFAULT_SERVER_SOCKET
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind(DEFAULT_SERVER_SOCKET)

        while True:
            file = socket.recv_string()
            response = ['']

            def add_response(part):
                response[0] = response[0] + '\n' + part
            try:
                translate_and_verify(file, jvm, args, add_response)
            except Exception as  e:
                response[0] = str(e)
            socket.send_string(response[0])
    else:
        translate_and_verify(args.vyper_file, jvm, args)


def translate_and_verify(vyper_file, jvm, args, print=print):
    try:
        start = time()
        tw = TwoVyper(jvm, args.model)
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
        print(vresult.to_string(args.ide_mode, args.show_viper_errors, include_model=args.model))
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
    except InvalidVyperException as e:
        print(e.message)
    except JException as e:
        print(e.stacktrace())
        raise e


if __name__ == '__main__':
    main()
