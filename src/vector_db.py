"""Vector Database handler for storing and retrieving documents"""
import os
import json
import numpy as np
from typing import List, Dict, Tuple, Optional
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from config.config import (
    VECTOR_DB_PATH,
    TOP_K,
    EMBEDDING_MODEL,
    USE_GEMINI,
)

# Import embeddings based on provider
if USE_GEMINI:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
else:
    from langchain_openai import OpenAIEmbeddings


class VectorDBManager:
    """Manages Vector Database operations"""

    def __init__(self):
        """Initialize the Vector DB Manager"""
        if USE_GEMINI:
            from config.config import GOOGLE_API_KEY
            os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
            self.embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
        else:
            from config.config import OPENAI_API_KEY
            os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
            self.embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        
        self.vector_store = None
        self.metadata_file = os.path.join(VECTOR_DB_PATH, "document_metadata.json")
        self.document_ids = {}  # Map: doc_id -> index
        self.load_or_create_store()
        self._load_metadata()

    def load_or_create_store(self):
        """Load existing vector store or create a new one"""
        if os.path.exists(VECTOR_DB_PATH):
            try:
                self.vector_store = FAISS.load_local(
                    VECTOR_DB_PATH, self.embeddings, allow_dangerous_deserialization=True
                )
                print(f"✓ Loaded vector store from {VECTOR_DB_PATH}")
            except Exception as e:
                print(f"Error loading vector store: {e}")
                self.vector_store = None
        else:
            print(f"No existing vector store found at {VECTOR_DB_PATH}")
            self.vector_store = None

    def _load_metadata(self):
        """Load document metadata from file"""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    self.document_ids = json.load(f)
                print(f"✓ Loaded metadata for {len(self.document_ids)} documents")
            except Exception as e:
                print(f"Error loading metadata: {e}")
                self.document_ids = {}
        else:
            self.document_ids = {}

    def _save_metadata(self):
        """Save document metadata to file"""
        try:
            os.makedirs(VECTOR_DB_PATH, exist_ok=True)
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.document_ids, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving metadata: {e}")

    def _rebuild_vector_store_without_ids(self, doc_ids_to_remove: List[str]) -> bool:
        """Rebuild vector store without specific document IDs"""
        if self.vector_store is None:
            return False

        try:
            # Get all current documents using the correct API
            all_docs = []
            docstore = self.vector_store.docstore
            
            # Access documents from docstore
            if hasattr(docstore, '_dict'):
                # InMemoryDocstore structure
                for doc_id, doc in docstore._dict.items():
                    if doc:
                        all_docs.append(doc)
            elif hasattr(docstore, 'search'):
                # Alternative structure
                try:
                    index_to_docstore_id = self.vector_store.index_to_docstore_id
                    for idx in range(len(index_to_docstore_id)):
                        doc_id = index_to_docstore_id[idx]
                        doc = docstore.search(doc_id)
                        if doc:
                            all_docs.append(doc)
                except:
                    pass

            # Filter out documents with IDs to remove
            filtered_docs = []
            for doc in all_docs:
                doc_id = doc.metadata.get("doc_id")
                if doc_id not in doc_ids_to_remove:
                    filtered_docs.append(doc)

            # Rebuild vector store
            if filtered_docs:
                self.vector_store = FAISS.from_documents(
                    filtered_docs, self.embeddings
                )
            else:
                self.vector_store = None

            return True
        except Exception as e:
            print(f"Error rebuilding vector store: {e}")
            return False

    def add_documents(self, documents: List[Document]) -> bool:
        """Add documents to the vector store, replacing if doc_id exists"""
        try:
            # Check for documents with doc_id and handle duplicates
            docs_to_add = []
            doc_ids_to_remove = set()

            for doc in documents:
                doc_id = doc.metadata.get("doc_id")
                if doc_id:
                    if doc_id in self.document_ids:
                        # Mark for removal
                        doc_ids_to_remove.add(doc_id)
                        print(f"  Document with id '{doc_id}' already exists, will be replaced")
                    self.document_ids[doc_id] = {
                        "content": doc.page_content[:100],
                        "source": doc.metadata.get("source", "unknown"),
                    }
                docs_to_add.append(doc)

            # Remove old documents if there are duplicates
            if doc_ids_to_remove:
                self._rebuild_vector_store_without_ids(list(doc_ids_to_remove))

            # Add new documents
            if self.vector_store is None:
                self.vector_store = FAISS.from_documents(
                    docs_to_add, self.embeddings
                )
            else:
                self.vector_store.add_documents(docs_to_add)

            self.save_store()
            print(f"✓ Added {len(docs_to_add)} documents to vector store")
            return True
        except Exception as e:
            print(f"Error adding documents: {e}")
            return False

    def retrieve_documents(
        self, query: str, k: int = TOP_K
    ) -> List[Tuple[Document, float]]:
        """Retrieve top k documents most similar to the query"""
        if self.vector_store is None:
            print("Vector store is empty")
            return []

        try:
            # Try a few possible method names across LangChain versions
            if hasattr(self.vector_store, "similarity_search_with_scores"):
                results = self.vector_store.similarity_search_with_scores(query, k=k)
                return results

            if hasattr(self.vector_store, "similarity_search_with_score"):
                results = self.vector_store.similarity_search_with_score(query, k=k)
                return results

            if hasattr(self.vector_store, "similarity_search"):
                docs = self.vector_store.similarity_search(query, k=k)
                # similarity_search returns List[Document] -> convert to (doc, None)
                return [(d, None) for d in docs]

            raise AttributeError("No known similarity_search method on vector_store")
        except Exception as e:
            print(f"Error retrieving documents: {e}")
            return []

    def save_store(self):
        """Save vector store to disk"""
        try:
            os.makedirs(VECTOR_DB_PATH, exist_ok=True)
            self.vector_store.save_local(VECTOR_DB_PATH)
            self._save_metadata()
            print(f"✓ Vector store saved to {VECTOR_DB_PATH}")
        except Exception as e:
            print(f"Error saving vector store: {e}")

    def get_store_info(self) -> Dict:
        """Get information about the vector store"""
        if self.vector_store is None:
            return {"status": "empty", "document_count": 0}

        return {
            "status": "loaded",
            "document_count": len(self.vector_store.docstore._dict),
            "unique_doc_ids": len(self.document_ids),
        }

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document by its doc_id"""
        if doc_id not in self.document_ids:
            print(f"Document with id '{doc_id}' not found")
            return False

        try:
            self._rebuild_vector_store_without_ids([doc_id])
            del self.document_ids[doc_id]
            self.save_store()
            print(f"✓ Deleted document with id '{doc_id}'")
            return True
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False

    def get_document_by_id(self, doc_id: str) -> Optional[Dict]:
        """Get document metadata by its doc_id"""
        return self.document_ids.get(doc_id)
