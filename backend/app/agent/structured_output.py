from __future__ import annotations

from typing import Any


class StructuredOutputValidationError(ValueError):
    pass


class StructuredOutputValidator:
    def validate(
        self,
        output: Any,
        *,
        allowed_place_ids: set[str] | None = None,
        allowed_rag_chunk_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(output, dict):
            raise StructuredOutputValidationError("structured output must be a JSON object")
        days = output.get("days")
        if not isinstance(days, list):
            raise StructuredOutputValidationError("structured output must include days[]")

        allowed_place_ids = allowed_place_ids or set()
        allowed_rag_chunk_ids = allowed_rag_chunk_ids or set()
        for day in days:
            if not isinstance(day, dict):
                raise StructuredOutputValidationError("each day must be an object")
            if not day.get("date"):
                raise StructuredOutputValidationError("each day must include date")
            items = day.get("items")
            if not isinstance(items, list):
                raise StructuredOutputValidationError("each day must include items[]")
            for item in items:
                if not isinstance(item, dict):
                    raise StructuredOutputValidationError("each item must be an object")
                if not item.get("temp_id") or not item.get("title"):
                    raise StructuredOutputValidationError("each item must include temp_id and title")
                place_id = item.get("place_id")
                if place_id and allowed_place_ids and place_id not in allowed_place_ids:
                    raise StructuredOutputValidationError(f"place_id was not returned by tools: {place_id}")

        citations = output.get("rag_citations", [])
        if not isinstance(citations, list):
            raise StructuredOutputValidationError("rag_citations must be a list")
        for citation in citations:
            chunk_id = citation.get("chunk_id") if isinstance(citation, dict) else citation
            if chunk_id and allowed_rag_chunk_ids and str(chunk_id) not in allowed_rag_chunk_ids:
                raise StructuredOutputValidationError(f"rag citation was not retrieved in this run: {chunk_id}")
        return output
