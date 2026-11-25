from typing import Annotated

from pydantic import BaseModel, ConfigDict, FiniteFloat, StringConstraints


class RegisterCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    jig: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    heat: FiniteFloat
    thick: FiniteFloat
    target: FiniteFloat


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


class RecordReading(Candidate):
    measured: FiniteFloat
