"""
Copyright (c) 2021 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""


# 2vyper tests based on pytest framework.

# 2vyper tests are based on ideas taken from ``Silver``. Each test is a
# Vyper source file with annotations that specify the expected behaviour.
# The goal of the test suite is to catch changes in the behaviour,
# therefore, annotations must be always up-to-date. Annotations are
# written in Vyper comments that start with ``::``. Multiple annotations
# on the same line are separated by ``|``.

# Supported annotation types are:

# 1.  ``ExpectedOutput(<backend>)(<error_id>, <via1>, <via2>,…)`` –
#     indicates that the following line should produce the specified
#     error.
# 2.  ``UnexpectedOutput(<backend>)(<error_id>, <issue>, <via1>, <via2>,…)``
#     – indicates that the following line should not produce the
#     specified error, but it currently does. The problem is currently
#     tracked in ``backend`` (if missing, then 2vyper) issue tracker's
#     issue ``issue``.
# 3.  ``MissingOutput(<backend>)(<error_id>, <issue>, <via1>, <via2>,…)`` –
#     indicates that the error mentioned in the matching
#     ``ExpectedOutput`` annotation is not produced due to issue
#     ``issue``.
# 4.  ``Label(<via>)`` – mark location to be used in other annotations.
# 5.  ``IgnoreFile(<issue>)`` – mark that file cannot be tested due to
#     critical issue such as a crash, which is tracked in ``issue``.

import abc
import os
import re
import tokenize
from typing import Any, Dict, List, Optional, Union

import pytest

# Change path such that the subsequent imports succeed
import context  # noqa

########################################################################################################################
#                           PLEASE BE CAUTIOUS WITH GLOBAL IMPORTS FROM THE TWOVYPER MODULE!                           #
#      THIS MODULE GETS RELOADED AND ANY REFERENCE MIGHT BE INVALID / FROM THE FIRST INSTANTIATION OF THE MODULE.      #
########################################################################################################################

from twovyper import config
from twovyper.exceptions import InvalidProgramException
from twovyper.main import prepare_twovyper_for_vyper_version
from twovyper.verification import TwoVyperError
from twovyper.verification.result import VerificationResult
from twovyper.viper.jvmaccess import JVM

VYPER_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)))

_JVM: Optional[JVM] = None
VERIFIER = 'silicon'


def _init_jvm(verifier):
    config.set_classpath(verifier)
    global _JVM
    _JVM = JVM(config.classpath)
    global VERIFIER
    VERIFIER = verifier


def _init_model(model):
    global OPTIONS_MODEL
    OPTIONS_MODEL = model


def _init_check_ast(check):
    global OPTIONS_CHECK_AST_INCONSISTENCIES
    OPTIONS_CHECK_AST_INCONSISTENCIES = check


def _init_store_viper(flag):
    global OPTIONS_STORE_VIPER
    OPTIONS_STORE_VIPER = flag


_BACKEND_SILICON = 'silicon'
_BACKEND_CARBON = 'carbon'
_BACKEND_ANY = 'ANY'

OPTIONS_MODEL = False

OPTIONS_CHECK_AST_INCONSISTENCIES = False

OPTIONS_STORE_VIPER = False


def _consume(key: str, dictionary: Dict[str, Any], check: bool = False) -> Any:
    """Destructive read from the dictionary.

    If ``check`` is ``True``, check that read value does not evaluate to
    ``false``.
    """
    value = dictionary[key]
    del dictionary[key]
    if check:
        assert value, "{} in {} is False".format(key, dictionary)
    return value


def _consume_list(key: str, dictionary: Dict[str, Any]) -> Any:
    """Destructive read of comma separated list from the dictionary."""
    value = _consume(key, dictionary)
    if value:
        return [part for part in value.split(', ') if part]
    else:
        return []


class Error(abc.ABC):
    """Base class for reported errors.

    Subclasses of this class are wrappers that unify interfaces of two
    error types currently produced by 2vyper:

    1.  Invalid program errors produced by translators.
    2.  Verification errors produced by back-end verifiers.
    """

    @property
    @abc.abstractmethod
    def full_id(self) -> str:
        """Return full error id."""

    @property
    @abc.abstractmethod
    def line(self) -> int:
        """Return line number."""

    @abc.abstractmethod
    def get_vias(self) -> List[int]:
        """Return a list of vias."""


class VerificationError(Error):
    """Verification error reported by verifier."""

    def __init__(self, actual_error: TwoVyperError) -> None:
        self._error = actual_error

    def __repr__(self) -> str:
        return f'VerificationError({self.full_id}, line={self.line}, vias={self.get_vias()})'

    @property
    def full_id(self) -> str:
        return self._error.full_id

    @property
    def line(self) -> int:
        return self._error.position.line

    def get_vias(self) -> List[int]:
        from twovyper.verification import error_manager
        error_pos = self._error.position
        if error_pos.node_id:
            vias = error_manager.get_vias(error_pos.node_id)
            return [via.position.line() for via in vias]
        reason_pos = self._error.reason.position
        if reason_pos.node_id:
            vias = error_manager.get_vias(reason_pos.node_id)
            if vias:
                return [via.position.line() for via in vias]
        return []


class InvalidProgramError(Error):
    """Invalid program error reported by translator."""

    def __init__(self, exception: InvalidProgramException) -> None:
        self._exception = exception

    def __repr__(self) -> str:
        return f'InvalidProgramError({self.full_id}, line={self.line}, vias={self.get_vias()})'

    @property
    def full_id(self) -> str:
        return f'{self._exception.code}:{self._exception.reason_code}'

    @property
    def line(self) -> int:
        return self._exception.node.lineno

    def get_vias(self) -> List[int]:
        return []


class Annotation:
    """Base class for all test annotations."""

    def __init__(
            self, token: tokenize.TokenInfo,
            group_dict: Dict[str, Optional[str]]) -> None:
        self._token = token
        for key, value in group_dict.items():
            if key == 'type':
                continue
            if value:
                setter_name = '_set_' + key
                # Here we check that provided annotation does not have
                # too much stuff.
                assert hasattr(self, setter_name), (
                    "Unsupported {} for {}".format(value, self))
                getattr(self, setter_name)(value)

    @property
    def line(self) -> int:
        """Get line number of this annotation."""
        return self._token.start[0] + 1

    @property
    @abc.abstractmethod
    def backend(self) -> str:
        """Back-end which this annotation is targeting."""

    def get_vias(self) -> List[int]:
        return []


class BackendSpecificAnnotationMixIn(Annotation, abc.ABC):
    """Annotation that depends on the back-end.

    The subclass is expected to define a field ``_backend``.
    """

    def __init__(self, token: tokenize.TokenInfo, group_dict: Dict[str, Optional[str]]):
        if not hasattr(self, '_backend'):
            self._backend: Optional[str] = None
        super().__init__(token, group_dict)

    @property
    def backend(self) -> str:
        """Back-end which this annotation is targeting."""
        return self._backend or _BACKEND_ANY


class ErrorMatchingAnnotationMixIn(Annotation, abc.ABC):
    """An annotation that can match an error.

    The subclass is expected to define fields ``_id`` and ``_labels``.
    """

    def __init__(self, token: tokenize.TokenInfo, group_dict: Dict[str, Optional[str]]):
        if not hasattr(self, '_id'):
            self._id: str = ''
        super().__init__(token, group_dict)

    def match(self, error: Error) -> bool:
        """Check is error matches this annotation."""
        return (self._id == error.full_id and
                (self.line == error.line or
                 (self.line == 2 and error.line == 1)) and
                self.get_vias() == error.get_vias())


class UsingLabelsAnnotationMixIn(Annotation, abc.ABC):
    """An annotation that can refer to labels.

    The subclass is expected to define the field ``_labels``.
    """
    def __init__(self, token: tokenize.TokenInfo, group_dict: Dict[str, Optional[str]]):
        if not hasattr(self, '_labels'):
            self._labels: List[Union[str, 'LabelAnnotation']] = []
        super().__init__(token, group_dict)

    def resolve_labels(self, labels_dict: Dict[str, 'LabelAnnotation']) -> None:
        """Resolve label names to label objects."""
        for i, label in enumerate(self._labels):
            self._labels[i] = labels_dict[label]

    def get_vias(self) -> List[int]:
        """Return vias extracted from label positions."""
        return [label.line for label in self._labels]


class ExpectedOutputAnnotation(
        BackendSpecificAnnotationMixIn,
        ErrorMatchingAnnotationMixIn,
        UsingLabelsAnnotationMixIn,
        Annotation):
    """ExpectedOutput annotation."""

    def __init__(
            self, token: tokenize.TokenInfo,
            group_dict: Dict[str, Optional[str]]) -> None:
        """ExpectedOutput constructor.

        Supported info:

        +   id – mandatory.
        +   backend – optional.
        +   labels – optional.
        """
        self._id = _consume('id', group_dict, True)
        self._backend = _consume('backend', group_dict)
        self._labels = _consume_list('labels', group_dict)
        super().__init__(token, group_dict)

    def __repr__(self) -> str:
        return 'ExpectedOutput({}, line={}, vias={})'.format(
            self._id, self.line, self.get_vias())

    @property
    def full_id(self) -> str:
        """Return full error id."""
        return self._id


class UnexpectedOutputAnnotation(
        BackendSpecificAnnotationMixIn,
        ErrorMatchingAnnotationMixIn,
        UsingLabelsAnnotationMixIn,
        Annotation):
    """UnexpectedOutput annotation."""

    def __init__(
            self, token: tokenize.TokenInfo,
            group_dict: Dict[str, Optional[str]]) -> None:
        """UnexpectedOutput constructor.

        Supported info:

        +   id – mandatory.
        +   backend – optional, ``None`` means ``2vyper``.
        +   issue_id – mandatory.
        +   labels – optional.
        """
        self._id = _consume('id', group_dict, True)
        self._backend = _consume('backend', group_dict)
        self._issue_id = _consume('issue_id', group_dict, True)
        self._labels = _consume_list('labels', group_dict)
        super().__init__(token, group_dict)

    def __repr__(self) -> str:
        return 'UnexpectedOutput({}, line={}, vias={})'.format(
            self._id, self.line, self.get_vias())


class MissingOutputAnnotation(
        BackendSpecificAnnotationMixIn,
        UsingLabelsAnnotationMixIn,
        Annotation):
    """MissingOutput annotation."""

    def __init__(
            self, token: tokenize.TokenInfo,
            group_dict: Dict[str, Optional[str]]) -> None:
        """MissingOutput constructor.

        Supported info:

        +   id – mandatory.
        +   backend – optional, ``None`` means ``2vyper``.
        +   issue_id – mandatory.
        +   labels – optional.
        """
        self._id = _consume('id', group_dict, True)
        self._backend = _consume('backend', group_dict)
        self._issue_id = _consume('issue_id', group_dict, True)
        self._labels = _consume_list('labels', group_dict)
        super().__init__(token, group_dict)

    def match(self, expected: ExpectedOutputAnnotation) -> bool:
        """Check if this annotation matches the given ``ExpectedOutput``.

        ``MissingOutput`` annotation indicates that the output mentioned
        in a certain ``ExpectedOutput`` annotation is not going to be
        produced due to some issue. In other words, a ``MissingOutput``
        annotation silences a matching ``ExpectedOutput`` annotation.
        Intuitively, a ``MissingOutput`` annotation matches an
        ``ExpectedOutput`` annotation if they are on the same line and
        have the same arguments.
        """
        return (self.line == expected.line and
                self._id == expected.full_id and
                self.get_vias() == expected.get_vias() and
                (self.backend == expected.backend or
                 self.backend == _BACKEND_ANY or
                 expected.backend == _BACKEND_ANY))


class LabelAnnotation(Annotation):
    """Label annotation."""

    def __init__(
            self, token: tokenize.TokenInfo,
            group_dict: Dict[str, Optional[str]]) -> None:
        """Label constructor.

        Supported info:

        +   id – mandatory.
        """
        self._id = _consume('id', group_dict, True)
        super().__init__(token, group_dict)

    @property
    def name(self) -> str:
        """Return the labels name."""
        return self._id

    @property
    def backend(self) -> str:
        """Back-end which this annotation is targeting."""
        return _BACKEND_ANY


class IgnoreFileAnnotation(
        BackendSpecificAnnotationMixIn,
        Annotation):
    """IgnoreFile annotation."""

    def __init__(
            self, token: tokenize.TokenInfo,
            group_dict: Dict[str, Optional[str]]) -> None:
        """IgnoreFile constructor.

        Supported info:

        +   id – mandatory, used as issue_id.
        +   backend – optional, ``None`` means ``2vyper``.
        """
        self._issue_id = _consume('id', group_dict, True)
        assert self._issue_id.isnumeric(), "Issue id must be a number."
        self._backend = _consume('backend', group_dict)
        super().__init__(token, group_dict)


class AnnotationManager:
    """A class for managing annotations in the specific test file."""

    def __init__(self, backend: str) -> None:
        self._matcher = re.compile(
            # Annotation type such as ExpectedOutput.
            r'(?P<type>[a-zA-Z]+)'
            # To which back-end the annotation is dedicated. None means
            # both.
            r'(\((?P<backend>[a-z]+)\))?'
            r'\('
            # Error message, or label id. Matches everything except
            # comma.
            r'(?P<id>[a-zA-Z.()_\-:;\d ?\'"]+)'
            # Issue id in the issue tracker.
            r'(, (?P<issue_id>\d+))?'
            # Labels. Note that label must start with a letter.
            r'(?P<labels>(, [a-zA-Z][a-zA-Z\d_]+)+)?'
            r'\)'
        )
        self._annotations = {
            'ExpectedOutput': [],
            'UnexpectedOutput': [],
            'MissingOutput': [],
            'Label': [],
            'IgnoreFile': [],
        }
        self._backend = backend

    def _create_annotation(self, annotation_string: str, token: tokenize.TokenInfo) -> None:
        """Create annotation object from the ``annotation_string``."""
        match = self._matcher.match(annotation_string)
        assert match, "Failed to match: {}".format(annotation_string)
        group_dict = match.groupdict()
        annotation_type = group_dict['type']
        if annotation_type == 'ExpectedOutput':
            annotation = ExpectedOutputAnnotation(token, group_dict)
        elif annotation_type == 'UnexpectedOutput':
            annotation = UnexpectedOutputAnnotation(token, group_dict)
        elif annotation_type == 'MissingOutput':
            annotation = MissingOutputAnnotation(token, group_dict)
        elif annotation_type == 'Label':
            annotation = LabelAnnotation(token, group_dict)
        elif annotation_type == 'IgnoreFile':
            annotation = IgnoreFileAnnotation(token, group_dict)
        else:
            assert False, "Unknown annotation type: {}".format(annotation_type)
        assert annotation_type in self._annotations
        if annotation.backend in (self._backend, _BACKEND_ANY):
            self._annotations[annotation_type].append(annotation)

    def _get_expected_output(self) -> List[ExpectedOutputAnnotation]:
        """Return a final list of expected output annotations."""
        expected_annotations = self._annotations['ExpectedOutput']
        missing_annotations = set(self._annotations['MissingOutput'])
        # Filter out annotations that should be missing.
        annotations = []
        for expected in expected_annotations:
            for missing in missing_annotations:
                if missing.match(expected):
                    missing_annotations.remove(missing)
                    break
            else:
                annotations.append(expected)
        assert not missing_annotations
        # Append unexpected annotations.
        annotations.extend(self._annotations['UnexpectedOutput'])
        return annotations

    def resolve_references(self) -> None:
        """Resolve references to labels."""
        labels_dict = dict(
            (label.name, label)
            for label in self._annotations['Label'])
        for annotation_type in ['ExpectedOutput', 'UnexpectedOutput',
                                'MissingOutput']:
            for annotation in self._annotations[annotation_type]:
                annotation.resolve_labels(labels_dict)

    def check_errors(self, actual_errors: List[Error]) -> None:
        """Check if actual errors match annotations."""
        annotations = set(self._get_expected_output())
        unexpected_errors = []
        for error in actual_errors:
            for annotation in annotations:
                if annotation.match(error):
                    annotations.remove(annotation)
                    break
            else:
                unexpected_errors.append(error)

        umsg = "\n".join(f"{error}" for error in unexpected_errors)
        assert not unexpected_errors, f"Unexpected errors found:\n{umsg}"
        assert not annotations

    def has_unexpected_missing(self) -> bool:
        """Check if there are unexpected or missing output annotations."""
        return len(self._annotations['UnexpectedOutput'] or
                   self._annotations['MissingOutput']) > 0

    def extract_annotations(self, token: tokenize.TokenInfo) -> None:
        """Extract annotations mentioned in the token."""
        content = token.string.strip()[3:]
        stripped_list = [part.strip() for part in content.split('|')]
        for part in stripped_list:
            self._create_annotation(part, token)

    def ignore_file(self) -> bool:
        """Check if file should be ignored."""
        return bool(self._annotations['IgnoreFile'])


class AnnotatedTest:
    """A class representing an annotated test.

    An annotated test is a Python source file with annotations that
    indicate expected verification errors.
    """

    @staticmethod
    def _is_annotation(token: tokenize.TokenInfo) -> bool:
        """Check if token is a test annotation.

        A test annotation is a comment starting with ``#::``.
        """
        return (token.type is tokenize.COMMENT and
                token.string.strip().startswith('#:: ') and
                token.string.strip().endswith(')'))

    def get_annotation_manager(
            self, path: str, backend: str) -> AnnotationManager:
        """Create ``AnnotationManager`` for given Python source file."""
        manager = AnnotationManager(backend)
        with open(path, 'rb') as fp:
            for token in tokenize.tokenize(fp.readline):
                if self._is_annotation(token):
                    manager.extract_annotations(token)
        manager.resolve_references()
        return manager


class TwoVyperTest(AnnotatedTest):
    """Test for testing correct behavior of 2vyper for annotated programs."""

    def test_file(self, path: str, jvm: JVM, verifier: str, store_viper: bool):
        """Test specific Vyper file."""
        annotation_manager = self.get_annotation_manager(path, verifier)
        if annotation_manager.ignore_file():
            pytest.skip('Ignored')
        abspath = os.path.abspath(path)
        prepare_twovyper_for_vyper_version(abspath)
        from twovyper.main import TwoVyper
        tw = TwoVyper(jvm, OPTIONS_MODEL, OPTIONS_CHECK_AST_INCONSISTENCIES)
        from twovyper.exceptions import InvalidProgramException
        try:
            prog = tw.translate(abspath, vyper_root=VYPER_ROOT)
        except InvalidProgramException as e:
            actual_errors = [InvalidProgramError(e)]
            annotation_manager.check_errors(actual_errors)
            if annotation_manager.has_unexpected_missing():
                pytest.skip('Unexpected or missing output')
        else:
            if store_viper:
                import string
                valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
                file_name = "".join(x for x in path if x in valid_chars) + '.vpr'
                dir_name = 'viper_out'
                if not os.path.exists(dir_name):
                    os.makedirs(dir_name)
                file_path = os.path.join(dir_name, file_name)
                with open(file_path, 'w') as fp:
                    fp.write(str(prog))
            verification_result: VerificationResult = tw.verify(prog, abspath, verifier)
            self._evaluate_result(verification_result, annotation_manager, jvm)

    @staticmethod
    def _evaluate_result(verification_result: VerificationResult,
                         annotation_manager: AnnotationManager, jvm: JVM):
        """Evaluate verification result with regard to test annotations."""
        if verification_result:
            actual_errors = []
        else:
            from twovyper.verification.result import Failure
            assert isinstance(verification_result, Failure)
            assert all(
                isinstance(error.pos(), jvm.viper.silver.ast.HasLineColumn)
                for error in verification_result.errors)
            actual_errors = [
                VerificationError(error) for error in verification_result.errors]
            # if False:  # sif
            #     # carbon will report all functional errors twice, as we model two
            #     # executions, therefore we filter duplicated errors here.
            #     # (Note: we don't make errors unique, just remove one duplicate)
            #     distinct = []
            #     reprs = map(lambda e: e.__repr__(), actual_errors)
            #     repr_counts = Counter(reprs)
            #     repr_counts = dict(map(lambda rc: (rc[0], -(-rc[1] // 2)),
            #                            repr_counts.items()))
            #     for err in actual_errors:
            #         if repr_counts[err.__repr__()] > 0:
            #             distinct.append(err)
            #             repr_counts[err.__repr__()] -= 1
            #     actual_errors = distinct
        annotation_manager.check_errors(actual_errors)
        if annotation_manager.has_unexpected_missing():
            pytest.skip('Unexpected or missing output')


_TESTER = TwoVyperTest()


def _test(path):
    """Execute provided verification test."""
    _TESTER.test_file(path, _JVM, VERIFIER, OPTIONS_STORE_VIPER)
