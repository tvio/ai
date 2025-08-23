#!/usr/bin/env python3
"""
Krok 4b: Vektorové vyhledávání v extrahovaných informacích o lécích
Používá sentence transformers pro embedding a pgvector pro similarity search
"""

import pg8000
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import json

# Nastavení logování
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VectorSearchManager:
    """Třída pro vektorové vyhledávání v extrahovaných informacích"""
    
    def __init__(self, host: str = "localhost", port: int = 5432, 
                 database: str = "test", user: str = "test", password: str = "test"):
        self.connection_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
        
        # Inicializace sentence transformer modelu
        logger.info("Načítám sentence transformer model...")
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        logger.info("Model načten")
        
        self.init_vector_tables()
    
    def init_vector_tables(self):
        """Vytvoří tabulky pro vektorové vyhledávání"""
        try:
            with pg8000.connect(**self.connection_params) as conn:
                with conn.cursor() as cursor:
                    
                    # Kontrola pgvector rozšíření
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    logger.info("pgvector rozšíření aktivováno")
                    
                    # Tabulka pro vektory extrahovaných informací
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS medicine_vectors (
                            id SERIAL PRIMARY KEY,
                            kod_sukl VARCHAR(20) REFERENCES leciva(kod_sukl) UNIQUE,
                            indikace_vector vector(384),
                            davkovani_vector vector(384),
                            combined_vector vector(384),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    logger.info("Tabulka medicine_vectors vytvořena")
                    
                    # Index pro rychlé vyhledávání
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_medicine_vectors_combined 
                        ON medicine_vectors 
                        USING ivfflat (combined_vector vector_cosine_ops)
                        WITH (lists = 100)
                    """)
                    logger.info("Vektorový index vytvořen")
                    
                    conn.commit()
                    logger.info("Vektorové tabulky inicializovány")
                    
        except Exception as e:
            logger.error(f"Chyba při inicializaci vektorových tabulek: {e}")
            raise
    
    def create_embeddings(self, text: str) -> np.ndarray:
        """Vytvoří embedding pro daný text"""
        try:
            # Vytvoření embeddingu
            embedding = self.model.encode(text)
            return embedding
        except Exception as e:
            logger.error(f"Chyba při vytváření embeddingu: {e}")
            return np.zeros(384)  # Prázdný vektor jako fallback
    
    def update_vectors_for_medicine(self, kod_sukl: str, indikace: List[str], davkovani: List[str]) -> bool:
        """Aktualizuje vektory pro konkrétní lék"""
        try:
            # Kombinace textů pro embedding
            indikace_text = " ".join(indikace) if indikace else ""
            davkovani_text = " ".join(davkovani) if davkovani else ""
            combined_text = f"{indikace_text} {davkovani_text}".strip()
            
            if not combined_text:
                logger.warning(f"Prázdný text pro {kod_sukl}")
                return False
            
            # Vytvoření embeddingů
            indikace_vector = self.create_embeddings(indikace_text)
            davkovani_vector = self.create_embeddings(davkovani_text)
            combined_vector = self.create_embeddings(combined_text)
            
            # Uložení do databáze
            with pg8000.connect(**self.connection_params) as conn:
                with conn.cursor() as cursor:
                    
                    cursor.execute("""
                        INSERT INTO medicine_vectors (
                            kod_sukl, indikace_vector, davkovani_vector, combined_vector
                        ) VALUES (%s, %s, %s, %s)
                        ON CONFLICT (kod_sukl) DO UPDATE SET
                            indikace_vector = EXCLUDED.indikace_vector,
                            davkovani_vector = EXCLUDED.davkovani_vector,
                            combined_vector = EXCLUDED.combined_vector
                    """, (
                        kod_sukl,
                        indikace_vector.tolist(),
                        davkovani_vector.tolist(),
                        combined_vector.tolist()
                    ))
                    
                    conn.commit()
                    logger.info(f"Vektory aktualizovány pro {kod_sukl}")
                    return True
                    
        except Exception as e:
            logger.error(f"Chyba při aktualizaci vektorů pro {kod_sukl}: {e}")
            return False
    
    def search_similar_medicines(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Vyhledá léky podobné dotazu pomocí vektorového vyhledávání"""
        try:
            # Vytvoření embeddingu pro dotaz
            query_vector = self.create_embeddings(query)
            
            with pg8000.connect(**self.connection_params) as conn:
                with conn.cursor() as cursor:
                    
                    # Vektorové vyhledávání s cosine similarity
                    cursor.execute("""
                        SELECT l.kod_sukl, l.nazev, ei.indikace, ei.davkovani,
                               1 - (mv.combined_vector <=> %s) as similarity
                        FROM leciva l
                        JOIN extracted_info ei ON l.kod_sukl = ei.kod_sukl
                        JOIN medicine_vectors mv ON l.kod_sukl = mv.kod_sukl
                        ORDER BY mv.combined_vector <=> %s
                        LIMIT %s
                    """, (
                        query_vector.tolist(),
                        query_vector.tolist(),
                        limit
                    ))
                    
                    results = []
                    for row in cursor.fetchall():
                        results.append({
                            'kod_sukl': row[0],
                            'nazev': row[1],
                            'indikace': row[2] if row[2] else [],
                            'davkovani': row[3] if row[3] else [],
                            'similarity': round(float(row[4]), 3)
                        })
                    
                    return results
                    
        except Exception as e:
            logger.error(f"Chyba při vektorovém vyhledávání: {e}")
            return []
    
    def search_by_symptoms(self, symptoms: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Vyhledá léky podle příznaků (indikací)"""
        try:
            # Vytvoření embeddingu pro příznaky
            symptoms_vector = self.create_embeddings(symptoms)
            
            with pg8000.connect(**self.connection_params) as conn:
                with conn.cursor() as cursor:
                    
                    # Vyhledávání v indikacích
                    cursor.execute("""
                        SELECT l.kod_sukl, l.nazev, ei.indikace, ei.davkovani,
                               1 - (mv.indikace_vector <=> %s) as similarity
                        FROM leciva l
                        JOIN extracted_info ei ON l.kod_sukl = ei.kod_sukl
                        JOIN medicine_vectors mv ON l.kod_sukl = mv.kod_sukl
                        ORDER BY mv.indikace_vector <=> %s
                        LIMIT %s
                    """, (
                        symptoms_vector.tolist(),
                        symptoms_vector.tolist(),
                        limit
                    ))
                    
                    results = []
                    for row in cursor.fetchall():
                        results.append({
                            'kod_sukl': row[0],
                            'nazev': row[1],
                            'indikace': row[2] if row[2] else [],
                            'davkovani': row[3] if row[3] else [],
                            'similarity': round(float(row[4]), 3)
                        })
                    
                    return results
                    
        except Exception as e:
            logger.error(f"Chyba při vyhledávání podle příznaků: {e}")
            return []
    
    def batch_update_vectors(self) -> int:
        """Hromadně aktualizuje vektory pro všechny léky"""
        try:
            updated_count = 0
            
            with pg8000.connect(**self.connection_params) as conn:
                with conn.cursor() as cursor:
                    
                    # Získání všech léků s extrahovanými informacemi
                    cursor.execute("""
                        SELECT ei.kod_sukl, ei.indikace, ei.davkovani
                        FROM extracted_info ei
                        LEFT JOIN medicine_vectors mv ON ei.kod_sukl = mv.kod_sukl
                        WHERE mv.kod_sukl IS NULL
                    """)
                    
                    medicines = cursor.fetchall()
                    logger.info(f"Načteno {len(medicines)} léků k aktualizaci vektorů")
                    
                    for kod_sukl, indikace, davkovani in medicines:
                        if self.update_vectors_for_medicine(kod_sukl, indikace, davkovani):
                            updated_count += 1
                        
                        # Pauza mezi zpracováním
                        if updated_count % 10 == 0:
                            logger.info(f"Aktualizováno {updated_count}/{len(medicines)} vektorů")
            
            logger.info(f"✅ Hromadná aktualizace dokončena: {updated_count} vektorů")
            return updated_count
            
        except Exception as e:
            logger.error(f"Chyba při hromadné aktualizaci vektorů: {e}")
            return 0

def main():
    """Hlavní funkce pro testování vektorového vyhledávání"""
    logger.info("🔍 Testuji vektorové vyhledávání v extrahovaných informacích")
    
    # Inicializace vektorového manažeru
    vector_manager = VectorSearchManager()
    
    # 1. Hromadná aktualizace vektorů
    logger.info("Aktualizuji vektory pro všechny léky...")
    updated_count = vector_manager.batch_update_vectors()
    
    if updated_count == 0:
        logger.info("Žádné vektory k aktualizaci")
    
    # 2. Test vektorového vyhledávání
    test_queries = [
        "lék na bolest",
        "proti horečce", 
        "na kašel",
        "antibiotikum",
        "proti zánětu"
    ]
    
    for query in test_queries:
        logger.info(f"\n🔍 Test vyhledávání: '{query}'")
        results = vector_manager.search_similar_medicines(query, limit=5)
        
        if results:
            logger.info(f"Nalezeno {len(results)} léků:")
            for result in results:
                logger.info(f"  • {result['nazev']} (similarity: {result['similarity']})")
                logger.info(f"    Indikace: {', '.join(result['indikace'][:2])}")
        else:
            logger.info("Žádné výsledky")
    
    # 3. Test vyhledávání podle příznaků
    logger.info(f"\n🔍 Test vyhledávání podle příznaků: 'bolest hlavy'")
    symptom_results = vector_manager.search_by_symptoms("bolest hlavy", limit=5)
    
    if symptom_results:
        logger.info(f"Nalezeno {len(symptom_results)} léků na bolest hlavy:")
        for result in symptom_results:
            logger.info(f"  • {result['nazev']} (similarity: {result['similarity']})")
    else:
        logger.info("Žádné výsledky pro bolest hlavy")

if __name__ == "__main__":
    main()
