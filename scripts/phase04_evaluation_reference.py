"""Synthetic post-decision association only; never imported by selection.

No real label loader or molecular-success evaluator is implemented here.
The adapter does not import this module or create an evaluation_reference.
"""

from types import MappingProxyType

if __package__:
    from .phase04_prediction_index import Decision
else:
    from phase04_prediction_index import Decision

FUTURE_REAL_PROTOCOL = MappingProxyType({
    "enabled": False, "metric": "BiSyRMSD", "comparison": "<",
    "threshold_angstrom": 2.0, "status": "BLOCKED_REQUIRES_SEPARATE_REVIEW",
})


class EvaluationReference:
    """A separate synthetic mapping, not a field on any inference object.

    This API separation is not an OS sandbox against arbitrary Python code.
    Payloads are test data; no reference is opened by preflight or ranking.
    """

    __slots__ = ("_singletons", "_by_run")

    def __init__(self, singletons, by_run, *, synthetic_only=False):
        if synthetic_only is not True:
            raise ValueError("Real evaluation reference access is disabled")
        self._singletons = MappingProxyType({target: tuple(chains) for target, chains in singletons.items()})
        self._by_run = MappingProxyType({key: MappingProxyType(dict(payload)) for key, payload in by_run.items()})


def associate_after_selection(decisions, evaluation_reference, *, synthetic_only=False):
    """Attach a lone reference to an already selected whole-system run.

    Never search candidates, repair a selection, or calculate success. Missing
    references change association status only, not the supplied decisions.
    """
    if synthetic_only is not True:
        raise ValueError("Real post-decision evaluation remains disabled")
    if type(decisions) is not tuple or any(type(d) is not Decision for d in decisions):
        raise TypeError("Association requires finalized Decision objects")
    if type(evaluation_reference) is not EvaluationReference:
        raise TypeError("Expected a separate synthetic EvaluationReference")
    associations = []
    for decision in decisions:
        run = decision.selected
        ligands = evaluation_reference._singletons.get(run.target, ())
        payload = evaluation_reference._by_run.get(run.identity)
        status = ("blocked_not_single_reference" if len(ligands) != 1 or not ligands[0]
                  else "reference_unavailable" if payload is None else "synthetic_association_only")
        associations.append({
            "run_identity": run.identity, "status": status,
            "reference_ligand": ligands[0] if len(ligands) == 1 else None,
            "evaluation_reference": payload if status == "synthetic_association_only" else None,
        })
    return tuple(associations)
