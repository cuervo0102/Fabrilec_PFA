import chromadb

CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "fabrilec_tenders"

print("Chroma path:", CHROMA_PATH)

client = chromadb.PersistentClient(path=CHROMA_PATH)

collections = client.list_collections()

print("Collections:", collections)

collection = client.get_collection(COLLECTION_NAME)

print("Collection:", collection.name)
print("Number of chunks:", collection.count())



from collections import Counter

allm = collection.get(include=["metadatas"])["metadatas"]
print(allm[0])                                       
print(Counter(m.get("tender_ref") for m in allm))     