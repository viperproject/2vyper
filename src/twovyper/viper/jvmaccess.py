"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import jpype


class JVM:
    """
    Encapsulates access to a JVM
    """

    def __init__(self, classpath: str):
        jvm_path = jpype.getDefaultJVMPath()
        path_arg = f'-Djava.class.path={classpath}'
        jpype.startJVM(jvm_path, path_arg, '-Xss48m', convertStrings=False)
        self.java = jpype.JPackage('java')
        self.scala = jpype.JPackage('scala')
        self.viper = jpype.JPackage('viper')
        self.fastparse = jpype.JPackage('fastparse')

    def is_known_class(self, class_object) -> bool:
        return not isinstance(class_object, jpype.JPackage)
