# -*- coding: utf-8 -*-
from abc import abstractmethod, ABC
from typing import Set

from pythomata import PropInt

from flloat.base.convertible import ConvertibleFormula, BaseConvertibleFormula
from flloat.base.delta import (
    Delta,
    DeltaConvertibleFormula,
    EquivalenceDeltaConvertible,
    ImpliesDeltaConvertible,
)
from flloat.base.formulas import (
    Formula,
    CommutativeBinaryOperator,
    UnaryOperator,
    BinaryOperator,
    OperatorChildren,
    AtomicFormula,
)
from flloat.base.nnf import NNF, NotNNF, DualBinaryOperatorNNF, DualNNF, AtomicNNF
from flloat.base.symbols import Symbols, Symbol
from flloat.base.truths import NotTruth, AndTruth, OrTruth, Truth, FiniteTrace, FiniteTraceTruth
from flloat.flloat import to_automaton
from flloat.pl import PLFormula, PLTrue, PLFalse, PLAnd, PLOr, PLAtomic


class RegExpTruth(Truth):
    @abstractmethod
    def truth(self, tr: FiniteTrace, start: int = 0, end: int = 0):
        raise NotImplementedError


class LDLfFormula(Formula, FiniteTraceTruth, NNF, Delta):

    def delta(self, i: PropInt, epsilon=False):

        f = self.to_nnf()
        if epsilon is False:
            d = f._delta(i)
        else:
            # By definition, if epsilon=True, then the result must be either True or False.
            # The output is a Propositional Formula with only True or False as atomics.
            # Hence, we just evaluate the formula with the empty propositional interpretation.
            d = f._delta(None, epsilon)
            d = PLTrue() if d.truth({}) else PLFalse()
        return d

    @abstractmethod
    def _delta(self, i: PropInt, epsilon=False):
        """apply delta function, assuming that 'self' is a LDLf formula in Negative Normal Form"""
        raise NotImplementedError

    def __repr__(self):
        return self.__str__()

    def to_automaton(self):
        return to_automaton(self)


class LDLfCommBinaryOperator(CommutativeBinaryOperator, LDLfFormula, ABC):
    pass


class DeltaRegExp(ABC):

    @abstractmethod
    def delta_diamond(self, f: LDLfFormula, i: PropInt, epsilon=False):
        raise NotImplementedError

    @abstractmethod
    def delta_box(self, f: LDLfFormula, i: PropInt, epsilon=False):
        raise NotImplementedError


class RegExpFormula(Formula, RegExpTruth, NNF, DeltaRegExp, ABC):

    # this should be never called. Just for override the inherited abstract method.
    def negate(self):
        raise NotImplementedError


class LDLfTemporalFormula(LDLfFormula, ABC):

    @property
    def temporal_brackets(self) -> str:
        raise NotImplementedError

    def __init__(self, r: RegExpFormula, f: LDLfFormula):
        super().__init__()
        self.r = r
        self.f = f

    def _members(self):
        return self.temporal_brackets, self.r, self.f

    def __str__(self):
        return (
            self.temporal_brackets[0]
            + str(self.r)
            + self.temporal_brackets[1]
            + "("
            + str(self.f)
            + ")"
        )

    def find_labels(self) -> Set[Symbol]:
        return self.f.find_labels().union(self.r.find_labels())


class LDLfTemporalFormulaNNF(LDLfTemporalFormula, DualNNF, ABC):
    def _to_nnf(self):
        return type(self)(self.r.to_nnf(), self.f.to_nnf())

    def negate(self):
        return self.Dual(self.r, LDLfNot(self.f))


class LDLfAtomic(AtomicFormula, AtomicNNF, LDLfFormula, ABC):

    def __str__(self):
        return AtomicFormula.__str__(self)

    def find_labels(self):
        return AtomicFormula.find_labels(self)


class LDLfLogicalTrue(LDLfAtomic):
    def __init__(self):
        super().__init__(Symbols.LOGICAL_TRUE.value)

    def find_labels(self):
        return set()

    def truth(self, *args):
        return True

    def _to_nnf(self):
        return self

    def negate(self):
        return LDLfLogicalFalse()

    def _delta(self, i: PropInt, epsilon=False):
        return PLTrue()


class LDLfLogicalFalse(LDLfFormula, BaseConvertibleFormula):

    def __str__(self):
        return Symbols.LOGICAL_FALSE.value

    def find_labels(self):
        return set()

    def convert(self):
        return LDLfNot(LDLfLogicalTrue())

    def _delta(self, i: PropInt, epsilon=False):
        return PLFalse()

    def _members(self):
        return Symbols.LOGICAL_FALSE.value


class LDLfNot(NotTruth, LDLfFormula, NotNNF):

    def _to_nnf(self):
        if isinstance(self.f, AtomicNNF) and not isinstance(self.f, BaseConvertibleFormula):
            return self.f.negate()
        else:
            return self.f.negate().to_nnf()

    def _delta(self, i: PropInt, epsilon=False):
        if epsilon:
            return PLFalse()

        result = self.f._delta(i, epsilon=epsilon)
        if result == PLTrue():
            return PLFalse()
        else:
            return PLTrue()


class LDLfAnd(LDLfCommBinaryOperator, AndTruth, DualBinaryOperatorNNF):
    def _delta(self, i: PropInt, epsilon=False):
        return PLAnd([f._delta(i, epsilon) for f in self.formulas])


class LDLfOr(LDLfCommBinaryOperator, OrTruth, DualBinaryOperatorNNF):
    def _delta(self, i: PropInt, epsilon=False):
        return PLOr([f._delta(i, epsilon) for f in self.formulas])


class LDLfImplies(ImpliesDeltaConvertible, LDLfFormula):
    And = LDLfAnd
    Or = LDLfOr
    Not = LDLfNot


class LDLfEquivalence(EquivalenceDeltaConvertible, LDLfCommBinaryOperator):
    And = LDLfAnd
    Or = LDLfOr
    Not = LDLfNot


class LDLfDiamond(LDLfTemporalFormulaNNF, FiniteTraceTruth):
    temporal_brackets = "<>"

    def truth(self, i: FiniteTrace, pos: int = 0):
        # last + 1 in order to include the last step
        return any(
            self.r.truth(i, pos, j) and self.f.truth(i, j) for j in range(pos, len(i))
        )

    def _delta(self, i: PropInt, epsilon=False):
        return self.r.delta_diamond(self.f, i, epsilon)


class LDLfBox(ConvertibleFormula, LDLfTemporalFormulaNNF):
    temporal_brackets = "[]"

    def convert(self):
        return LDLfNot(LDLfDiamond(self.r, LDLfNot(self.f)))

    def truth(self, i: FiniteTrace, pos: int = 0):
        return self.convert().truth(i, pos)

    def _delta(self, i: PropInt, epsilon=False):
        return self.r.delta_box(self.f, i, epsilon)


class RegExpPropositional(RegExpFormula):

    def __init__(self, pl_formula: PLFormula):
        RegExpFormula.__init__(self)
        self.pl_formula = pl_formula

    def truth(self, tr: FiniteTrace, start: int = 0, end: int = 0):
        return (
            end == start + 1
            and end <= len(tr) - 1
            and self.pl_formula.truth(tr[start])
        )

    def _members(self):
        return RegExpPropositional, self.pl_formula

    def __str__(self):
        return str(self.pl_formula)

    def _to_nnf(self):
        return RegExpPropositional(self.pl_formula.to_nnf())

    def negate(self):
        return RegExpPropositional(self.pl_formula.negate())

    def delta_diamond(self, f: LDLfFormula, i: PropInt, epsilon=False):
        if epsilon:
            return PLFalse()
        if self.pl_formula.truth(i):
            return PLAtomic(_expand(f))
        else:
            return PLFalse()

    def delta_box(self, f: LDLfFormula, i: PropInt, epsilon=False):
        if epsilon:
            return PLTrue()
        if self.pl_formula.truth(i):
            return PLAtomic(_expand(f))
        else:
            return PLTrue()

    def find_labels(self):
        return self.pl_formula.find_labels()


class RegExpTest(UnaryOperator, RegExpFormula):
    operator_symbol = Symbols.PATH_TEST.value

    # def __init__(self, f:LDLfFormula):
    #     RegExpFormula.__init__(self)
    #     UnaryOperator.__init__(self, f)

    def truth(self, tr: FiniteTrace, start: int = 0, end: int = 0):
        return start == end and self.f.truth(tr, start)

    def __str__(self):
        s = super().__str__()
        s = s[1:] + s[0]
        return s

    def _to_nnf(self):
        return RegExpTest(self.f.to_nnf())

    def negate(self):
        return self.Dual(self.Not(self.f))

    def delta_diamond(self, f: LDLfFormula, i: PropInt, epsilon=False):
        return PLAnd([self.f._delta(i, epsilon), f._delta(i, epsilon)])

    def delta_box(self, f: LDLfFormula, i: PropInt, epsilon=False):
        # ff = LDLfNot(self.f).to_nnf()
        # dff = ff._delta(i, epsilon)
        # fun = f._delta(i, epsilon)
        return PLOr([LDLfNot(self.f).to_nnf()._delta(i, epsilon), f._delta(i, epsilon)])

    def find_labels(self):
        return self.f.find_labels()


class RegExpUnion(CommutativeBinaryOperator, RegExpFormula):
    operator_symbol = Symbols.PATH_UNION.value

    def __init__(self, formulas):
        RegExpFormula.__init__(self)
        CommutativeBinaryOperator.__init__(self, formulas)

    def truth(self, tr: FiniteTrace, start: int = 0, end: int = 0):
        return any(f.truth(tr, start, end) for f in self.formulas_set)

    def _to_nnf(self):
        return RegExpUnion([r.to_nnf() for r in self.formulas_set])

    def delta_diamond(self, f: LDLfFormula, i: PropInt, epsilon=False):
        return PLOr([LDLfDiamond(r, f)._delta(i, epsilon) for r in self.formulas_set])

    def delta_box(self, f: LDLfFormula, i: PropInt, epsilon=False):
        return PLAnd([LDLfBox(r, f)._delta(i, epsilon) for r in self.formulas_set])


class RegExpSequence(BinaryOperator, RegExpFormula):
    operator_symbol = Symbols.PATH_SEQUENCE.value

    def __init__(self, formulas: OperatorChildren):
        RegExpFormula.__init__(self)
        BinaryOperator.__init__(self, formulas)

    def truth(self, tr: FiniteTrace, start: int = 0, end: int = 0):
        f1 = self.formulas[0]
        if len(self.formulas) == 2:
            f2 = self.formulas[1]
        else:
            f2 = RegExpSequence(self.formulas[1:])


        l = [(f1.truth(tr, start, k), f2.truth(tr, k, end)) for k in range(start, end + 1)]

        return any(
            f1.truth(tr, start, k) and f2.truth(tr, k, end)
            for k in range(start, end + 1)
        )

    def _to_nnf(self):
        return RegExpSequence([r.to_nnf() for r in self.formulas])

    def delta_diamond(self, f: LDLfFormula, i: PropInt, epsilon=False):
        res = LDLfDiamond(self.formulas[-1], f)
        for r in reversed(self.formulas[:-1]):
            res = LDLfDiamond(r, res)
        return res._delta(i, epsilon)

    def delta_box(self, f: LDLfFormula, i: PropInt, epsilon=False):
        res = LDLfBox(self.formulas[-1], f)
        for r in reversed(self.formulas[:-1]):
            res = LDLfBox(r, res)
        return res._delta(i, epsilon)


class RegExpStar(UnaryOperator, RegExpFormula):
    operator_symbol = Symbols.PATH_STAR.value

    # def __init__(self, f):
    #     UnaryOperator.__init__(self, f)
    #     RegExpFormula.__init__(self)

    def truth(self, tr: FiniteTrace, start: int = 0, end: int = 0):
        return start == end or any(
            self.f.truth(tr, start, k) and self.truth(tr, k, end)
            for k in range(start, end + 1)
        )

    def __str__(self):
        s = super().__str__()
        s = s[1:] + s[0]
        return s

    def _to_nnf(self):
        return RegExpStar(self.f.to_nnf())

    def delta_diamond(self, f: LDLfFormula, i: PropInt, epsilon=False):
        return PLOr(
            [
                f._delta(i, epsilon),
                LDLfDiamond(self.f, _F(LDLfDiamond(self, f)))._delta(i, epsilon),
            ]
        )

    def delta_box(self, f: LDLfFormula, i: PropInt, epsilon=False):
        # subf = LDLfBox(self.f, _T(LDLfBox(self, f)))
        # k = subf._delta(i, epsilon)
        # l = [f._delta(i, epsilon), subf]
        # ff = PLAnd(l)
        return PLAnd(
            [
                f._delta(i, epsilon),
                LDLfBox(self.f, _T(LDLfBox(self, f)))._delta(i, epsilon),
            ]
        )


class LDLfPropositional(DeltaConvertibleFormula, LDLfFormula):
    def __init__(self, pl_formula: PLFormula):
        super().__init__()
        self.pl_formula = pl_formula

    def convert(self):
        return LDLfDiamond(RegExpPropositional(self.pl_formula), LDLfLogicalTrue())

    def _members(self):
        return LDLfPropositional, self.pl_formula

    def find_labels(self):
        return self.pl_formula.find_labels()

    def __str__(self):
        return str(self.convert())


class LDLfEnd(DeltaConvertibleFormula, LDLfAtomic):
    def __init__(self):
        super().__init__(Symbols.END.value)

    def find_labels(self):
        return set()

    def convert(self):
        return LDLfBox(RegExpPropositional(PLTrue()), LDLfLogicalFalse())


class LDLfLast(DeltaConvertibleFormula, LDLfAtomic, ):
    def __init__(self):
        super().__init__(Symbols.LAST.value)

    def find_labels(self):
        return set()

    def convert(self):
        return LDLfDiamond(RegExpPropositional(PLTrue()), LDLfEnd().convert())


class _F(LDLfFormula):

    def __init__(self, f: Formula):
        super().__init__()
        self.f = f

    def _members(self):
        return ("_F", self.f)

    def __str__(self):
        return "_".join(map(str, self._members()))

    def delta(self, i: PropInt, epsilon=False):
        return self._delta(i, epsilon)

    def _delta(self, i: PropInt, epsilon=False):
        return PLFalse()

    def _to_nnf(self):
        return self

    def negate(self):
        return _T(self.f)

    def find_labels(self):
        return super().find_labels()

    def truth(self, i: FiniteTrace, pos: int):
        raise NotImplementedError


class _T(LDLfFormula):

    def __init__(self, f: Formula):
        super().__init__()
        self.f = f

    def _members(self):
        return ("_T", self.f)

    def __str__(self):
        return "_".join(map(str, self._members()))

    def delta(self, i: PropInt, epsilon=False):
        return self._delta(i, epsilon)

    def _delta(self, i: PropInt, epsilon=False):
        return PLTrue()

    def _to_nnf(self):
        return self

    def negate(self):
        return _F(self.f)

    def find_labels(self):
        return super().find_labels()

    def truth(self, i: FiniteTrace, pos: int):
        raise NotImplementedError


def _expand(f: Formula):
    if isinstance(f, _F) or isinstance(f, _T):
        return _expand(f.f)
    # elif isinstance(f, LDLfLogicalTrue):
    #     return PLTrue()
    # elif isinstance(f, LDLfLogicalFalse):
    #     return PLFalse()
    elif isinstance(f, LDLfDiamond) or isinstance(f, LDLfBox):
        return type(f)(f.r, _expand(f.f))
    elif isinstance(f, BinaryOperator):
        return type(f)([_expand(subf) for subf in f.formulas])
    # elif isinstance(f, LDLfLogicalTrue):
    #     return PLTrue()
    # elif isinstance(f, LDLfLogicalFalse):
    #     return PLFalse()
    else:
        return f


AtomicNNF.Not = LDLfNot

LDLfAnd.Dual = LDLfOr
LDLfOr.Dual = LDLfAnd

LDLfDiamond.Dual = LDLfBox
LDLfBox.Dual = LDLfDiamond
