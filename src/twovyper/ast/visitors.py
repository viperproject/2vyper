"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Iterable, List, Optional, Tuple, Union

from twovyper.ast import ast_nodes as ast


def children(node: ast.Node) -> Iterable[Tuple[str, Union[Optional[ast.Node], List[ast.Node]]]]:
    for child in node.children:
        yield child, getattr(node, child)


# TODO: improve
def descendants(node: ast.Node) -> Iterable[ast.Node]:
    for _, child in children(node):
        if child is None:
            continue
        elif isinstance(child, ast.Node):
            yield child

            for child_child in descendants(child):
                yield child_child
        elif isinstance(child, List):
            for child_child in child:
                yield child_child
                for child_child_child in descendants(child_child):
                    yield child_child_child


class NodeVisitor:

    @property
    def method_name(self) -> str:
        return 'visit'

    def visit(self, node, *args):
        method = f'{self.method_name}_{node.__class__.__name__}'
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, *args)

    def visit_nodes(self, nodes: Iterable[ast.Node], *args):
        for node in nodes:
            self.visit(node, *args)
        return None

    def generic_visit(self, node, *args):
        for _, value in children(node):
            if value is None:
                continue
            elif isinstance(value, ast.Node):
                self.visit(value, *args)
            elif isinstance(value, list):
                for item in value:
                    self.visit(item, *args)
            else:
                assert False

        return None


class NodeTransformer(NodeVisitor):

    def generic_visit(self, node, *args):
        for field, old_value in children(node):
            if old_value is None:
                continue
            elif isinstance(old_value, ast.Node):
                new_node = self.visit(old_value, *args)
                if new_node is None:
                    delattr(node, field)
                else:
                    setattr(node, field, new_node)
            elif isinstance(old_value, list):
                new_values = []
                for value in old_value:
                    new_value = self.visit(value)
                    if new_value is None:
                        continue
                    else:
                        new_values.append(new_value)
                old_value[:] = new_values
            else:
                assert False

        return node
