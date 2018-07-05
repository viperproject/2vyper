"""
Example from "Principles of Secure Information Flow Analysis"
G. Smith
Malware Detection, 2007
"""

from nagini_contracts.contracts import *

def main(a: List[int], secret: int) -> int:
    Requires(list_pred(a))
    Requires(0 <= secret and secret < len(a))
    Requires(Low(a) and Low(len(a)) and Forall(range(0, len(a)), lambda el: a[el] is 0))
    Ensures(Low(Result()))
    a[secret] = 1
    # for i in range(0, len(a)):
    i = 0
    while i < len(a):
        Invariant(list_pred(a))
        Invariant(Low(len(a)))
        Invariant(0 <= i and i <= len(a))
        #:: ExpectedOutput(invariant.not.preserved:assertion.false)
        Invariant(Forall(range(0, len(a)), lambda el: Low(a[el])))
        Invariant(Low(i))
        if a[i] == 1:
            return i
        i += 1
    return 0

def main_fixed(a: List[int], secret: int) -> int:
    Requires(list_pred(a))
    Requires(0 <= secret and secret < len(a))
    Requires(Low(a) and Low(len(a)) and Forall(range(0, len(a)), lambda el: a[el] is 0))
    Ensures(Low(Result()))
    a[secret] = 1
    Declassify(secret)
    i = 0
    while i < len(a):
        Invariant(list_pred(a))
        Invariant(Low(len(a)))
        Invariant(0 <= i and i <= len(a))
        Invariant(Forall(range(0, len(a)), lambda el: Low(a[el])))
        Invariant(Low(i))
        if a[i] == 1:
            return i
        i += 1
    return 0
