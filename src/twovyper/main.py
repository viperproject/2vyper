"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import argparse
import logging
import os
import traceback

from typing import Set
from time import time

from jpype import JException

from twovyper import config
from twovyper import vyper

from twovyper.parsing import parser
from twovyper.analysis import analyzer
from twovyper.translation import translator

from twovyper.viper.jvmaccess import JVM
from twovyper.viper.typedefs import Program

from twovyper.verification import error_manager

from twovyper.verification.verifier import (
    Carbon,
    Silicon,
    VerificationResult,
    ViperVerifier
)

from twovyper.exceptions import (
    InvalidVyperException, UnsupportedException, InvalidProgramException, ConsistencyException
)


def translate(path: str, jvm: JVM, selected: Set[str] = set(),
              vyper_root=None, skip_vyper: bool = False,
              verbose: bool = False) -> Program:
    """
    Translates the Python module at the given path to a Viper program
    """
    path = os.path.abspath(path)
    error_manager.clear()

    # Check that the file is a valid Vyper contract
    if not skip_vyper:
        vyper.check(path, vyper_root)

    with open(path, 'r') as file:
        vyper_program = parser.parse(file.read(), path)
        analyzer.analyze(vyper_program)

    return translator.translate(vyper_program, path, jvm)


def verify(prog: Program, path: str,
           jvm: JVM, backend=ViperVerifier.silicon) -> VerificationResult:
    """
    Verifies the given Viper program
    """
    try:
        if backend == ViperVerifier.silicon:
            verifier = Silicon(jvm, path)
        elif backend == ViperVerifier.carbon:
            verifier = Carbon(jvm, path)
        vresult = verifier.verify(prog)
        return vresult
    except JException as je:
        print(je.stacktrace())
        traceback.print_exc()


def _parse_log_level(log_level_string: str) -> int:
    """ Parses the log level provided by the user.
    """
    LOG_LEVELS = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']

    log_level_string_upper = log_level_string.upper()
    if log_level_string_upper in LOG_LEVELS:
        return getattr(logging, log_level_string_upper, logging.WARNING)
    else:
        msg = 'Invalid logging level {0} (expected one of: {1})'.format(
            log_level_string,
            LOG_LEVELS)
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
        "-v",
        "--verbose",
        action="store_true",
        help="increase output verbosity"
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
        '--select',
        default=None,
        help='select specific methods or classes to verify, separated by commas'
    )
    parser.add_argument(
        '--server',
        action='store_true',
        help='Start Nagini server'
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

    jvm = JVM(config.classpath)
    if args.server:
        import zmq
        from twovyper.lib.constants import DEFAULT_SERVER_SOCKET
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind(DEFAULT_SERVER_SOCKET)
        global sil_programs
        # sil_programs = load_sil_files(jvm, args.sif)

        while True:
            file = socket.recv_string()
            response = ['']

            def add_response(part):
                response[0] = response[0] + '\n' + part

            translate_and_verify(file, jvm, args, add_response)
            socket.send_string(response[0])
    else:
        translate_and_verify(args.vyper_file, jvm, args)


def translate_and_verify(vyper_file, jvm, args, print=print):
    try:
        start = time()
        selected = set(args.select.split(',')) if args.select else set()
        prog = translate(vyper_file, jvm, selected, args.vyper_root, args.skip_vyper, args.verbose)
        if args.print_viper:
            if args.verbose:
                print('Result:')
            print(str(prog))
        if args.write_viper_to_file:
            with open(args.write_viper_to_file, 'w') as fp:
                fp.write(str(prog))
        if args.verifier == 'silicon':
            backend = ViperVerifier.silicon
        elif args.verifier == 'carbon':
            backend = ViperVerifier.carbon
        else:
            raise ValueError('Unknown verifier specified: ' + args.verifier)
        if args.benchmark >= 1:
            print("Run, Total, Start, End, Time")
            for i in range(args.benchmark):
                start = time()
                prog = translate(vyper_file, jvm, selected)
                vresult = verify(prog, vyper_file, jvm, backend=backend)
                end = time()
                print(f"{i}, {args.benchmark}, {start}, {end}, {end - start}")
        else:
            vresult = verify(prog, vyper_file, jvm, backend=backend)
        if args.verbose:
            print("Verification completed.")
        print(vresult.to_string(args.ide_mode, args.show_viper_errors))
        end = time()
        duration = end - start
        print(f"Verification took {duration:.2f} seconds.")
    except (InvalidProgramException, UnsupportedException) as e:
        print(e.error_string(vyper_file))
    except ConsistencyException as e:
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
