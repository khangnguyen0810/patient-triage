import json
import os
from pathlib import Path
import chromadb
from dotenv import load_dotenv

load_dotenv()

DATA_PATH = Path(__file__).parent.parent / "data" / "departments.json"


def seed():
    client = chromadb.CloudClient(
        api_key=os.environ["CHROMA_API_KEY"],
        tenant=os.environ["CHROMA_TENANT"],
        database=os.environ["CHROMA_DATABASE"],
    )
    collection = client.get_or_create_collection(name="hospital_routing")

    with open(DATA_PATH, "r") as f:
        records = json.load(f)

    documents = [r["document"] for r in records]
    metadatas = [{"department_name": r["department_name"]} for r in records]
    ids = [f"dept_id_{i}" for i in range(len(records))]

    collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
    print(f"[VectorDB] Seeded/updated {collection.count()} department routes.")


if __name__ == "__main__":
    seed()
