from collections.abc import Sequence

from fastapi import Query
from sqlalchemy import or_
from sqlalchemy.orm import Query as SQLAlchemyQuery


def pagination_params(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)) -> tuple[int, int]:
    return page, limit


def apply_search(query: SQLAlchemyQuery, search: str | None, fields: Sequence) -> SQLAlchemyQuery:
    if not search:
        return query
    pattern = f"%{search.strip()}%"
    return query.filter(or_(*(field.ilike(pattern) for field in fields)))


def apply_pagination(query: SQLAlchemyQuery, page: int, limit: int) -> SQLAlchemyQuery:
    offset = (page - 1) * limit
    return query.offset(offset).limit(limit)
