"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from twovyper.viper.jvmaccess import JVM
from twovyper.viper.typedefs import Program


class ViperParser:

    def __init__(self, jvm: JVM):
        self.jvm = jvm
        self.parser = getattr(getattr(jvm.viper.silver.parser, "FastParser$"), "MODULE$")
        self.parsed_success = getattr(jvm.fastparse.core, 'Parsed$Success')
        self._None = getattr(getattr(jvm.scala, 'None$'), 'MODULE$')

        assert self.parser
        assert self._None

    def parse(self, text: str, file: str) -> Program:
        jvm = self.jvm

        path = jvm.java.nio.file.Paths.get(file, [])
        parsed = self.parser.parse(text, path, self._None)

        assert isinstance(parsed, self.parsed_success)

        parse_result = parsed.value()
        parse_result.initProperties()
        resolver = jvm.viper.silver.parser.Resolver(parse_result)
        resolved = resolver.run()
        resolved = resolved.get()
        translator = jvm.viper.silver.parser.Translator(resolved)
        # Reset messages in global Consistency object. Otherwise, left-over
        # translation errors from previous translations prevent loading of the
        # built-in silver files.
        jvm.viper.silver.ast.utility.Consistency.resetMessages()
        program = translator.translate()
        return program.get()
