# src/triage_system/tools/rag_tool.py
import chromadb
from typing import List


class DepartmentRAGTool:
    def __init__(self, database_path: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=database_path)
        self.collection = self.client.get_or_create_collection(name="hospital_routing")
        if self.collection.count() == 0:
            self._seed_vector_knowledge_base()

    def _seed_vector_knowledge_base(self):

        print("[VectorDB] Collection empty. Seeding clinic knowledge base...")

        departments = [
            "Cardiology",
            "Neurology",
            "Orthopedics",
            "Gastroenterology",
            "Pulmonology",
        ]

        documents = [
            "Deals with cardiovascular health, chest pain, heart palpitations, chronic high blood pressure, and stroke risks.",
            "Deals with central nervous systems, brain injuries, migraines, chronic dizziness, numbness, and tremors.",
            "Deals with skeletal systems, musculoskeletal issues, bone fractures, intense joint back pain, and muscle sprains.",
            "Deals with digestive tracks, severe abdominal cramps, persistent nausea, acid reflux, stomach bugs, and vomiting.",
            "Deals with respiratory systems, chronic coughs, wheezing, severe asthma, lung infections, and breathing congestion.",
        ]

        metadatas = [{"department_name": dept} for dept in departments]
        ids = [f"dept_id_{i}" for i in range(len(departments))]

        self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
        print(
            f"[VectorDB] Successfully indexed {self.collection.count()} domain routes."
        )

    def retrieve_relevant_departments(self, query: str, top_k: int = 5) -> List[dict]:
        """
        Returns richer results: name + distance, so the agent can reason
        about confidence rather than just getting a bare name list.
        """
        n = min(top_k, self.collection.count())
        results = self.collection.query(query_texts=[query], n_results=n)

        matches = []
        if results and results.get("metadatas") and results["metadatas"][0]:
            metadatas = results["metadatas"][0]
            distances = results.get("distances", [[None] * len(metadatas)])[0]
            for meta, dist in zip(metadatas, distances):
                if meta:
                    matches.append(
                        {
                            "department_name": meta["department_name"],
                            "distance": dist,
                        }
                    )
        return matches
