import hashlib
import json
from typing import Any, Callable

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import IdempotencyRecord


def execute_idempotent(
    db: Session,
    user_id: int,
    endpoint: str,
    key: str,
    request_data: Any,
    operation: Callable[[], Any],
) -> Any:
    key = key.strip()

    if not key:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key cannot be empty",
        )

    payload = jsonable_encoder(request_data)
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    request_hash = hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()

    filters = (
        IdempotencyRecord.user_id == user_id,
        IdempotencyRecord.endpoint == endpoint,
        IdempotencyRecord.key == key,
    )

    def handle_existing(record):
        if record.request_hash != request_hash:
            raise HTTPException(
                status_code=409,
                detail="Idempotency-Key was used with different data",
            )

        if record.status == "completed":
            return record.response_body

        raise HTTPException(
            status_code=409,
            detail="Request with this key is still processing",
        )

    existing = db.query(IdempotencyRecord).filter(*filters).first()

    if existing:
        return handle_existing(existing)

    record = IdempotencyRecord(
        user_id=user_id,
        endpoint=endpoint,
        key=key,
        request_hash=request_hash,
        status="processing",
    )
    db.add(record)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(IdempotencyRecord).filter(*filters).first()

        if existing:
            return handle_existing(existing)

        raise

    try:
        result = operation()
        response_body = jsonable_encoder(result)

        record = db.query(IdempotencyRecord).filter(*filters).first()
        record.response_body = response_body
        record.status = "completed"
        db.commit()

        return result

    except Exception:
        db.rollback()
        record = db.query(IdempotencyRecord).filter(*filters).first()

        if record and record.status == "processing":
            db.delete(record)
            db.commit()

        raise