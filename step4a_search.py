#!/usr/bin/env python3
"""
Krok 4a: Vyhledávání v extrahovaných informacích o lécích
Samostatný modul pro vyhledávání v databázi
"""

import pg8000
import logging
from typing import List, Dict, Any

# Nastavení logování
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MedicineSearcher:
    """Třída pro vyhledávání léků v extrahovaných informacích"""
    
    def __init__(self, host: str = "localhost", port: int = 5432, 
                 database: str = "test", user: str = "test", password: str = "test"):
        self.connection_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
    
    def search_medicines(self, query: str) -> List[Dict[str, Any]]:
        """Vyhledá léky podle dotazu"""
        try:
            with pg8000.connect(**self.connection_params) as conn:
                with conn.cursor() as cursor:
                    
                    # Jednoduché vyhledávání v extrahovaných informacích
                    cursor.execute("""
                        SELECT DISTINCT l.kod_sukl, l.nazev, ei.indikace, ei.davkovani
                        FROM leciva l
                        JOIN extracted_info ei ON l.kod_sukl = ei.kod_sukl
                        WHERE 
                            ei.indikace::text ILIKE %s OR
                            ei.davkovani::text ILIKE %s OR
                            l.nazev ILIKE %s
                        LIMIT 20
                    """, (f'%{query}%', f'%{query}%', f'%{query}%'))
                    
                    results = []
                    for row in cursor.fetchall():
                        results.append({
                            'kod_sukl': row[0],
                            'nazev': row[1],
                            'indikace': row[2] if row[2] else [],
                            'davkovani': row[3] if row[3] else []
                        })
                    
                    return results
                    
        except Exception as e:
            logger.error(f"Chyba při vyhledávání: {e}")
            return []
    
    def search_by_indication(self, indication: str) -> List[Dict[str, Any]]:
        """Vyhledá léky podle konkrétní indikace"""
        try:
            with pg8000.connect(**self.connection_params) as conn:
                with conn.cursor() as cursor:
                    
                    cursor.execute("""
                        SELECT DISTINCT l.kod_sukl, l.nazev, ei.indikace, ei.davkovani
                        FROM leciva l
                        JOIN extracted_info ei ON l.kod_sukl = ei.kod_sukl
                        WHERE ei.indikace::text ILIKE %s
                        LIMIT 20
                    """, (f'%{indication}%',))
                    
                    results = []
                    for row in cursor.fetchall():
                        results.append({
                            'kod_sukl': row[0],
                            'nazev': row[1],
                            'indikace': row[2] if row[2] else [],
                            'davkovani': row[3] if row[3] else []
                        })
                    
                    return results
                    
        except Exception as e:
            logger.error(f"Chyba při vyhledávání podle indikace: {e}")
            return []
    
    def search_by_dosage(self, dosage: str) -> List[Dict[str, Any]]:
        """Vyhledá léky podle dávkování"""
        try:
            with pg8000.connect(**self.connection_params) as conn:
                with conn.cursor() as cursor:
                    
                    cursor.execute("""
                        SELECT DISTINCT l.kod_sukl, l.nazev, ei.indikace, ei.davkovani
                        FROM leciva l
                        JOIN extracted_info ei ON l.kod_sukl = ei.kod_sukl
                        WHERE ei.davkovani::text ILIKE %s
                        LIMIT 20
                    """, (f'%{dosage}%',))
                    
                    results = []
                    for row in cursor.fetchall():
                        results.append({
                            'kod_sukl': row[0],
                            'nazev': row[1],
                            'indikace': row[2] if row[2] else [],
                            'davkovani': row[3] if row[3] else []
                        })
                    
                    return results
                    
        except Exception as e:
            logger.error(f"Chyba při vyhledávání podle dávkování: {e}")
            return []
    
    def get_medicine_details(self, kod_sukl: str) -> Dict[str, Any]:
        """Získá detailní informace o konkrétním léku"""
        try:
            with pg8000.connect(**self.connection_params) as conn:
                with conn.cursor() as cursor:
                    
                    cursor.execute("""
                        SELECT l.kod_sukl, l.nazev, ei.indikace, ei.davkovani, ei.extracted_text
                        FROM leciva l
                        JOIN extracted_info ei ON l.kod_sukl = ei.kod_sukl
                        WHERE l.kod_sukl = %s
                    """, (kod_sukl,))
                    
                    row = cursor.fetchone()
                    if row:
                        return {
                            'kod_sukl': row[0],
                            'nazev': row[1],
                            'indikace': row[2] if row[2] else [],
                            'davkovani': row[3] if row[3] else [],
                            'extracted_text': row[4] if row[4] else ""
                        }
                    else:
                        return {}
                    
        except Exception as e:
            logger.error(f"Chyba při získávání detailů léku {kod_sukl}: {e}")
            return {}

def main():
    """Hlavní funkce pro testování vyhledávání"""
    logger.info("🔍 Testuji vyhledávání v extrahovaných informacích")
    
    # Inicializace vyhledávače
    searcher = MedicineSearcher()
    
    # Test 1: Obecné vyhledávání
    logger.info("Test 1: Obecné vyhledávání pro 'krvácení'")
    results = searcher.search_medicines("krvácení")
    logger.info(f"Nalezeno {len(results)} léků pro 'krvácení'")
    for result in results[:3]:  # Zobrazíme první 3
        logger.info(f"  - {result['kod_sukl']}: {result['nazev']}")
    
    # Test 2: Vyhledávání podle indikace
    logger.info("\nTest 2: Vyhledávání podle indikace 'bolest'")
    results = searcher.search_by_indication("bolest")
    logger.info(f"Nalezeno {len(results)} léků pro indikaci 'bolest'")
    for result in results[:3]:
        logger.info(f"  - {result['kod_sukl']}: {result['nazev']}")
    
    # Test 3: Vyhledávání podle dávkování
    logger.info("\nTest 3: Vyhledávání podle dávkování 'tableta'")
    results = searcher.search_by_dosage("tableta")
    logger.info(f"Nalezeno {len(results)} léků pro dávkování 'tableta'")
    for result in results[:3]:
        logger.info(f"  - {result['kod_sukl']}: {result['nazev']}")
    
    # Test 4: Detailní informace o léku (pokud existuje)
    if results:
        first_medicine = results[0]['kod_sukl']
        logger.info(f"\nTest 4: Detailní informace o léku {first_medicine}")
        details = searcher.get_medicine_details(first_medicine)
        if details:
            logger.info(f"  Název: {details['nazev']}")
            logger.info(f"  Indikace: {details['indikace']}")
            logger.info(f"  Dávkování: {details['davkovani']}")
        else:
            logger.info("  Lék nebyl nalezen")

if __name__ == "__main__":
    main()
