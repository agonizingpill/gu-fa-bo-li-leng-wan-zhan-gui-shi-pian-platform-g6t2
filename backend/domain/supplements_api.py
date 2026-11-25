from fastapi import APIRouter, Depends

from core.auth import actor, allow
from core.audit import record
from core.db import transaction
from domain import supplements_service as service
from domain.supplements_schemas import Candidate, RecordReading, RegisterCandidate

router = APIRouter()


@router.get('/supplements')
def list_supplements(user=Depends(actor)):
    with transaction() as conn:
        return service.list_candidates(conn)


@router.post('/supplements/register-candidate')
def register_candidate(data: RegisterCandidate, user=Depends(actor)):
    allow(user, ('operator', 'reviewer'))
    with transaction() as conn:
        output = service.register_candidate(conn, user, data)
        record(conn, user, 'supplements.register_candidate')
        return output


@router.post('/supplements/claim')
def claim(user=Depends(actor)):
    allow(user, ('operator', 'reviewer'))
    with transaction() as conn:
        output = service.claim(conn, user)
        record(conn, user, 'supplements.claim')
        return output


@router.post('/supplements/record-reading')
def record_reading(data: RecordReading, user=Depends(actor)):
    allow(user, ('operator', 'reviewer'))
    with transaction() as conn:
        output = service.record_reading(conn, user, data)
        record(conn, user, 'supplements.record_reading')
        return output


@router.post('/supplements/witness')
def witness(data: Candidate, user=Depends(actor)):
    allow(user, ('reviewer',))
    with transaction() as conn:
        output = service.witness(conn, user, data)
        record(conn, user, 'supplements.witness')
        return output
