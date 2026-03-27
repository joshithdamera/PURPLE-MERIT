from __future__ import annotations

import json
from pathlib import Path
from typing import List

from langchain.schema import Document

from utils import PROCESSED_DIR, ensure_directories, is_placeholder_record, load_jsonl


class CatalogLoader:
    def __init__(self, data_dir: str | Path = PROCESSED_DIR):
        self.data_dir = Path(data_dir)
        ensure_directories()

    def load_courses(self) -> List[Document]:
        documents: list[Document] = []
        for row in load_jsonl(self.data_dir / "courses.jsonl"):
            if is_placeholder_record(row):
                continue
            documents.append(
                Document(
                    page_content=self._format_course(row),
                    metadata={
                        "type": "course",
                        "course_code": row["course_code"],
                        "title": row["title"],
                        "source_url": row["source_url"],
                        "catalog_year": row["catalog_year"],
                        "accessed_date": row["accessed_date"],
                    },
                )
            )
        return documents

    def load_requirements(self) -> List[Document]:
        documents: list[Document] = []
        for row in load_jsonl(self.data_dir / "requirements.jsonl"):
            if is_placeholder_record(row):
                continue
            documents.append(
                Document(
                    page_content=self._format_requirement(row),
                    metadata={
                        "type": "requirement",
                        "requirement_id": row["requirement_id"],
                        "program": row["program"],
                        "section": row["section"],
                        "source_url": row["source_url"],
                        "catalog_year": row["catalog_year"],
                        "accessed_date": row["accessed_date"],
                    },
                )
            )
        return documents

    def load_policies(self) -> List[Document]:
        documents: list[Document] = []
        for row in load_jsonl(self.data_dir / "policies.jsonl"):
            if is_placeholder_record(row):
                continue
            documents.append(
                Document(
                    page_content=self._format_policy(row),
                    metadata={
                        "type": "policy",
                        "policy_id": row["policy_id"],
                        "title": row["title"],
                        "category": row["category"],
                        "source_url": row["source_url"],
                        "catalog_year": row["catalog_year"],
                        "accessed_date": row["accessed_date"],
                    },
                )
            )
        return documents

    def load_all(self) -> List[Document]:
        documents: list[Document] = []
        documents.extend(self.load_courses())
        documents.extend(self.load_requirements())
        documents.extend(self.load_policies())
        return documents

    @staticmethod
    def _format_course(course_data: dict) -> str:
        prereqs = "; ".join(course_data.get("prerequisites", [])) or "None"
        coreqs = "; ".join(course_data.get("co_requisites", [])) or "None"
        notes = course_data.get("notes") or "None"
        return (
            f"COURSE: {course_data['course_code']} - {course_data['title']}\n"
            f"UNITS: {course_data['units']}\n"
            f"PREREQUISITES: {prereqs}\n"
            f"CO-REQUISITES: {coreqs}\n"
            f"DESCRIPTION: {course_data['description']}\n"
            f"NOTES: {notes}"
        )

    @staticmethod
    def _format_requirement(req_data: dict) -> str:
        payload = {
            "requirement_id": req_data["requirement_id"],
            "program": req_data["program"],
            "section": req_data["section"],
            "content": req_data["content"],
            "source_url": req_data["source_url"],
            "catalog_year": req_data["catalog_year"],
            "accessed_date": req_data["accessed_date"],
        }
        return json.dumps(payload, indent=2)

    @staticmethod
    def _format_policy(policy_data: dict) -> str:
        payload = {
            "policy_id": policy_data["policy_id"],
            "title": policy_data["title"],
            "category": policy_data["category"],
            "content": policy_data["content"],
            "source_url": policy_data["source_url"],
            "catalog_year": policy_data["catalog_year"],
            "accessed_date": policy_data["accessed_date"],
        }
        return json.dumps(payload, indent=2)

