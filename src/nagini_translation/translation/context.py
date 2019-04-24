"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""


class Context:
    
    def __init__(self):
        self.invariants = []
        
        self.all_vars = {}
        self.args = {}
        self.locals = {}
        self.types = {}

        self._break_label_counter = -1
        self._continue_label_counter = -1
        self.break_label = None
        self.continue_label = None

        self.result_var = None
        self.end_label = None

    def next_break_label(self) -> str:
        self._break_label_counter += 1
        return f"break_{self._break_label_counter}"

    def next_continue_label(self) -> str:
        self._continue_label_counter += 1
        return f"continue_{self._continue_label_counter}"
