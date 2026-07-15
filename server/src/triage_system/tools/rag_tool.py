# src/triage_system/tools/rag_tool.py
import chromadb
from typing import List, Dict
import os


class DepartmentRAGTool:
    def __init__(self):
        self.client = chromadb.CloudClient(
            api_key=os.environ["CHROMA_API_KEY"],
            tenant=os.environ["CHROMA_TENANT"],
            database=os.environ["CHROMA_DATABASE"],
        )
        self.collection = self.client.get_or_create_collection(name="hospital_routing")

    def retrieve_relevant_departments(self, query: str, top_k: int = 5) -> List[Dict]:
        n = min(top_k, self.collection.count())
        results = self.collection.query(query_texts=[query], n_results=n)
        matches = []
        if results and results.get("metadatas") and results["metadatas"][0]:
            metadatas = results["metadatas"][0]
            distances = results.get("distances", [[None] * len(metadatas)])[0]
            for meta, dist in zip(metadatas, distances):
                if meta:
                    matches.append(
                        {"department_name": meta["department_name"], "distance": dist}
                    )
        return matches
