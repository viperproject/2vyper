from threading import Lock

from py2viper_contracts.contracts import (
    Requires,
)
from py2viper_contracts.io import *
from py2viper_contracts.obligations import (
    MustRelease,
    MustTerminate,
)


def MustInvoke_callee_1(t1: Place) -> None:
    pass


def MustInvoke_caller_1(t1: Place) -> None:
    Requires(token(t1, 1))
    #:: ExpectedOutput(leak_check.failed:caller.has_unsatisfied_obligations)
    MustInvoke_callee_1(t1)


def MustInvoke_callee_2(t1: Place) -> None:
    Requires(MustTerminate(1))


#:: ExpectedOutput(leak_check.failed:method_body.leaks_obligations)
def MustInvoke_caller_2(t1: Place) -> None:
    Requires(token(t1, 1))
    MustInvoke_callee_2(t1)


#:: ExpectedOutput(leak_check.failed:method_body.leaks_obligations)
def MustInvoke_body(t1: Place) -> None:
    Requires(token(t1, 1))


def MustRelease_callee_1(lock: Lock) -> None:
    pass


def MustRelease_caller_1(lock: Lock) -> None:
    Requires(MustRelease(lock, 1))
    #:: ExpectedOutput(leak_check.failed:caller.has_unsatisfied_obligations)
    MustRelease_callee_1(lock)


def MustRelease_callee_2(lock: Lock) -> None:
    Requires(MustTerminate(1))


#:: ExpectedOutput(leak_check.failed:method_body.leaks_obligations)
def MustRelease_caller_2(lock: Lock) -> None:
    Requires(MustRelease(lock, 1))
    MustRelease_callee_2(lock)


#:: ExpectedOutput(leak_check.failed:method_body.leaks_obligations)
def MustRelease_body(lock: Lock) -> None:
    Requires(MustRelease(lock, 1))
