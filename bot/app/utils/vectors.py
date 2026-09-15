from __future__ import annotations


def normalize_vector(vector: list[float], dimensions: int) -> list[float]:
    """Force a vector to a fixed dimensionality for pgvector storage."""
    if dimensions <= 0:
        raise ValueError("dimensions must be positive")
    if len(vector) == dimensions:
        return list(vector)
    if len(vector) > dimensions:
        return list(vector[:dimensions])
    return list(vector) + [0.0] * (dimensions - len(vector))


def vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(str(x) for x in embedding) + "]"
