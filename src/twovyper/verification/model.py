"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Callable, Dict, Optional, Tuple

from twovyper.utils import seq_to_list

from twovyper.viper.typedefs import AbstractVerificationError


ModelTransformation = Callable[[str, str], Tuple[str, str]]


class Model:

    def __init__(self, error: AbstractVerificationError, transform: Optional[ModelTransformation]):
        self._model = error.parsedModel().get()
        print(self._model)
        self._transform = transform
        self.values()

    def values(self) -> Dict[str, str]:
        res = {}
        if self._model and self._transform:
            entries = self._model.entries()
            for name_entry in seq_to_list(entries):
                name = str(name_entry._1())
                value = str(name_entry._2())
                transformation = self._transform(name, value)
                if transformation:
                    name, value = transformation
                    res[name] = value

        return res

    def __str__(self):
        return "\n".join(f"   {name} = {value}" for name, value in self.values().items())
