from collections.abc import Mapping, Sequence
from typing import Literal, cast

from sqlalchemy import or_
from sqlalchemy.orm import Query as SQLAlchemyQuery


def apply_search(query: SQLAlchemyQuery, search: str | None, fields: Sequence) -> SQLAlchemyQuery:
    if not search:
        return query
    pattern = f"%{search.strip()}%"
    return query.filter(or_(*(field.ilike(pattern) for field in fields)))


def apply_sort(
    query: SQLAlchemyQuery,
    sort_by: str | None,
    sort_order: str,
    allowed_fields: Mapping[str, object],
    default_fields: Sequence[object],
) -> SQLAlchemyQuery:
    order: Literal["asc", "desc"] = cast(Literal["asc", "desc"], sort_order)
    sort_column = allowed_fields.get(sort_by) if sort_by else None
    if sort_column is not None:
        ordered_column = sort_column.desc() if order == "desc" else sort_column.asc()
        return query.order_by(ordered_column)
    return query.order_by(*default_fields)


def build_paginated_response(query: SQLAlchemyQuery, page: int, limit: int) -> dict[str, object]:
    total = query.count()
    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()
    return {"items": items, "total": total, "page": page, "limit": limit}
