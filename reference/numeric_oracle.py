"""Host-only numerical tolerance oracle; never asserts backend execution."""
import math


class NumericComparisonError(ValueError):
    pass


def _scalar(value):
    return type(value) in (int, float) and math.isfinite(value)


def compare_vectors(expected, observed, *, atol=0.0, rtol=0.0, max_elements=100000):
    """Elementwise finite numeric comparison with explicit absolute/relative tolerance."""
    if type(expected) not in (list, tuple) or type(observed) not in (list, tuple):
        raise NumericComparisonError("vectors must be lists or tuples")
    if type(max_elements) is not int or not 0 <= max_elements <= 1000000:
        raise NumericComparisonError("invalid element budget")
    if len(expected) != len(observed) or len(expected) > max_elements:
        raise NumericComparisonError("vector shape mismatch or exceeded budget")
    if not _scalar(atol) or not _scalar(rtol) or atol < 0 or rtol < 0:
        raise NumericComparisonError("tolerances must be finite nonnegative scalars")
    failures = []
    for i, (wanted, got) in enumerate(zip(expected, observed)):
        if not _scalar(wanted) or not _scalar(got):
            raise NumericComparisonError("nonfinite, boolean or nonnumeric vector element")
        if not math.isclose(wanted, got, rel_tol=rtol, abs_tol=atol):
            failures.append(i)
    return {"passed": len(failures) == 0, "elements": len(expected),
            "failed_indices": failures}


def require_guest_evidence(metadata):
    """Metadata admission only; a digest must be checked by an independent runner."""
    if type(metadata) is not dict or set(metadata) != {
        "backend", "source_sha", "execution", "evidence_sha256"
    }:
        raise NumericComparisonError("invalid evidence metadata shape")
    import re
    sha40 = re.compile("[0-9a-f]{40}", re.ASCII)
    sha64 = re.compile("[0-9a-f]{64}", re.ASCII)
    if metadata["execution"] != "guest" or (
        type(metadata["source_sha"]) is not str or not sha40.fullmatch(metadata["source_sha"])
    ) or (
        type(metadata["evidence_sha256"]) is not str or not sha64.fullmatch(metadata["evidence_sha256"])
    ) or type(metadata["backend"]) is not str or not metadata["backend"]:
        raise NumericComparisonError("missing exact-head guest-execution metadata")
    return True
