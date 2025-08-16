#!/usr/bin/env python3
"""
Krok 3: Extrakce informací z PDF dokumentů pomocí AI
"""

import requests
import pg8000
import json
import time
from typing import List, Dict, Any, Optional
import logging
import pdfplumber
import ollama
from io import BytesIO

# Nastavení logování
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFExtractor:
    """Třída pro extrakci textu z PDF"""
    
    def __init__(self):
        self.ollama_client = ollama.Client()
    
    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extrahuje text z PDF dokumentu"""
        try:
            with BytesIO(pdf_content) as pdf_file:
                with pdfplumber.open(pdf_file) as pdf:
                    text = ""
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    
                    logger.info(f"Extrahováno {len(text)} znaků textu z PDF")
                    return text
                    
        except Exception as e:
            logger.error(f"Chyba při extrakci textu z PDF: {e}")
            return ""
    
    def extract_medicine_info(self, text: str, kod_sukl: str) -> Dict[str, Any]:
        """Extrahuje informace o léku pomocí AI modelu"""
        try:
            # Prompt pro AI model
            prompt = f"""
            Analyzuj následující text z SPC (Souhrn údajů o přípravku) pro lék s kódem SÚKL: {kod_sukl}
            
            Extrahuj následující informace a vrať je v JSON formátu:
            
            {{
                "indikace": ["seznam indikací pro použití léku"],
                "kontraindikace": ["seznam kontraindikací"],
                "ucinky": ["hlavní účinky léku"],
                "zpusob_podani": ["způsoby podání"],
                "davkovani": ["informace o dávkování"],
                "nežádoucí_účinky": ["možné nežádoucí účinky"],
                "interakce": ["lékové interakce"],
                "skupina": ["farmakologická skupina"],
                "mechanismus": ["mechanismus účinku"]
            }}
            
            Text SPC:
            {text[:3000]}  # Více textu pro lepší analýzu
            
            Vrať pouze JSON, žádné další texty.
            """
            
            # Volání AI modelu
            response = self.ollama_client.chat(
                model='gemma3',  # Vrátíme se k Gemma3 pro lepší češtinu
                messages=[{
                    'role': 'user',
                    'content': prompt
                }],
                options={
                    'num_ctx': 4096,  # Větší kontext pro lepší analýzu
                    'num_thread': 8,  # Více vláken pro rychlost
                    'temperature': 0.3  # Vyšší teplota pro kreativnější analýzu
                }
            )
            
            # Parsování JSON odpovědi
            try:
                # Ollama vrací response jako dict
                content = response['message']['content']
                result = json.loads(content)
                logger.info(f"Úspěšně extrahovány informace pro {kod_sukl}")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Chyba při parsování JSON odpovědi pro {kod_sukl}: {e}")
                logger.error(f"Odpověď: {content}")
                return {}
            except (KeyError, TypeError) as e:
                logger.error(f"Chyba při přístupu k odpovědi pro {kod_sukl}: {e}")
                logger.error(f"Typ odpovědi: {type(response)}")
                return {}
                
        except Exception as e:
            logger.error(f"Chyba při AI extrakci pro {kod_sukl}: {e}")
            return {}

class DatabaseManager:
    """Rozšířený správce databáze pro ukládání extrahovaných informací"""
    
    def __init__(self, host: str = "localhost", port: int = 5432, 
                 database: str = "test", user: str = "test", password: str = "test"):
        self.connection_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
        self.init_extraction_tables()
    
    def init_extraction_tables(self):
        """Vytvoří tabulky pro extrahované informace"""
        try:
            logger.info("Připojuji k databázi...")
            with pg8000.connect(**self.connection_params) as conn:
                logger.info("Připojení úspěšné, vytvářím tabulky...")
                with conn.cursor() as cursor:
                    
                    # Tabulka pro extrahované informace
                    logger.info("Vytvářím tabulku extracted_info...")
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS extracted_info (
                            id SERIAL PRIMARY KEY,
                            kod_sukl VARCHAR(20) REFERENCES leciva(kod_sukl),
                            indikace TEXT[],
                            kontraindikace TEXT[],
                            ucinky TEXT[],
                            zpusob_podani TEXT[],
                            davkovani TEXT[],
                            nezadouci_ucinky TEXT[],
                            interakce TEXT[],
                            skupina TEXT[],
                            mechanismus TEXT[],
                            extracted_text TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    logger.info("Tabulka extracted_info vytvořena")
                    
                    # Tabulka pro vyhledávání
                    logger.info("Vytvářím tabulku search_index...")
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS search_index (
                            id SERIAL PRIMARY KEY,
                            kod_sukl VARCHAR(20) REFERENCES leciva(kod_sukl),
                            klicove_slovo VARCHAR(100),
                            typ_informace VARCHAR(50),
                            relevance INTEGER DEFAULT 1,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    logger.info("Tabulka search_index vytvořena")
                    
                    conn.commit()
                    logger.info("Tabulky pro extrakci inicializovány")
                    
        except Exception as e:
            logger.error(f"Chyba při inicializaci tabulek pro extrakci: {e}")
            raise
    
    def save_extracted_info(self, kod_sukl: str, extracted_info: Dict[str, Any], 
                          extracted_text: str) -> bool:
        """Uloží extrahované informace do databáze"""
        try:
            with pg8000.connect(**self.connection_params) as conn:
                with conn.cursor() as cursor:
                    
                    cursor.execute("""
                        INSERT INTO extracted_info (
                            kod_sukl, indikace, kontraindikace, ucinky, zpusob_podani,
                            davkovani, nezadouci_ucinky, interakce, skupina, mechanismus,
                            extracted_text
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (kod_sukl) DO UPDATE SET
                            indikace = EXCLUDED.indikace,
                            kontraindikace = EXCLUDED.kontraindikace,
                            ucinky = EXCLUDED.ucinky,
                            zpusob_podani = EXCLUDED.zpusob_podani,
                            davkovani = EXCLUDED.davkovani,
                            nezadouci_ucinky = EXCLUDED.nezadouci_ucinky,
                            interakce = EXCLUDED.interakce,
                            skupina = EXCLUDED.skupina,
                            mechanismus = EXCLUDED.mechanismus,
                            extracted_text = EXCLUDED.extracted_text
                    """, (
                        kod_sukl,
                        extracted_info.get('indikace', []),
                        extracted_info.get('kontraindikace', []),
                        extracted_info.get('ucinky', []),
                        extracted_info.get('zpusob_podani', []),
                        extracted_info.get('davkovani', []),
                        extracted_info.get('nežádoucí_účinky', []),
                        extracted_info.get('interakce', []),
                        extracted_info.get('skupina', []),
                        extracted_info.get('mechanismus', []),
                        extracted_text[:1000]  # Omezíme délku uloženého textu
                    ))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Chyba při ukládání extrahovaných informací pro {kod_sukl}: {e}")
            return False
    
    def search_medicines(self, query: str) -> List[Dict[str, Any]]:
        """Vyhledá léky podle dotazu"""
        try:
            with pg8000.connect(**self.connection_params) as conn:
                with conn.cursor() as cursor:
                    
                    # Jednoduché vyhledávání v extrahovaných informacích
                    cursor.execute("""
                        SELECT DISTINCT l.kod_sukl, l.nazev, ei.indikace, ei.ucinky
                        FROM leciva l
                        JOIN extracted_info ei ON l.kod_sukl = ei.kod_sukl
                        WHERE 
                            ei.indikace::text ILIKE %s OR
                            ei.ucinky::text ILIKE %s OR
                            ei.skupina::text ILIKE %s OR
                            l.nazev ILIKE %s
                        LIMIT 20
                    """, (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
                    
                    results = []
                    for row in cursor.fetchall():
                        results.append({
                            'kod_sukl': row[0],
                            'nazev': row[1],
                            'indikace': row[2] if row[2] else [],
                            'ucinky': row[3] if row[3] else []
                        })
                    
                    return results
                    
        except Exception as e:
            logger.error(f"Chyba při vyhledávání: {e}")
            return []

def main():
    """Hlavní funkce pro extrakci informací z PDF"""
    logger.info("🚀 Začínám extrakci informací z PDF dokumentů")
    
    # Inicializace
    extractor = PDFExtractor()
    db_manager = DatabaseManager()
    
    # Načtení dokumentů z databáze
    try:
        logger.info("Připojuji k databázi pro načtení dokumentů...")
        with pg8000.connect(**db_manager.connection_params) as conn:
            logger.info("Připojení úspěšné, spouštím dotaz...")
            with conn.cursor() as cursor:
                
                # Získáme léky s dokumenty, které ještě nebyly zpracovány
                logger.info("Spouštím SQL dotaz pro načtení léků...")
                query = """
                    SELECT DISTINCT l.kod_sukl, l.nazev, d.pdf_data
                    FROM leciva l
                    JOIN dokumenty d ON l.kod_sukl = d.kod_sukl
                    WHERE d.typ = 'spc'
                    AND l.kod_sukl NOT IN (
                        SELECT kod_sukl FROM extracted_info
                    )
                    LIMIT 2
                """
                logger.info(f"SQL dotaz: {query}")
                cursor.execute(query)
                
                medicines = cursor.fetchall()
                logger.info(f"Načteno {len(medicines)} léků k zpracování")
                
                for i, (kod_sukl, nazev, pdf_data) in enumerate(medicines, 1):
                    logger.info(f"Zpracovávám {i}/{len(medicines)}: {kod_sukl} - {nazev}")
                    
                    try:
                        # 1. Extrakce textu z PDF
                        text = extractor.extract_text_from_pdf(pdf_data)
                        if not text:
                            logger.warning(f"Prázdný text pro {kod_sukl}")
                            continue
                        
                        # 2. AI extrakce informací
                        extracted_info = extractor.extract_medicine_info(text, kod_sukl)
                        if not extracted_info:
                            logger.warning(f"Prázdné extrahované informace pro {kod_sukl}")
                            continue
                        
                        # 3. Uložení do databáze
                        if db_manager.save_extracted_info(kod_sukl, extracted_info, text):
                            logger.info(f"✅ Informace uloženy pro {kod_sukl}")
                        else:
                            logger.error(f"❌ Chyba při ukládání pro {kod_sukl}")
                        
                        # Kratší pauza mezi zpracováním pro rychlost
                        time.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Chyba při zpracování {kod_sukl}: {e}")
                        continue
                
                # Test vyhledávání
                logger.info("🔍 Test vyhledávání...")
                results = db_manager.search_medicines("krvácení")
                logger.info(f"Nalezeno {len(results)} léků pro 'krvácení'")
                for result in results[:3]:  # Zobrazíme první 3
                    logger.info(f"  - {result['kod_sukl']}: {result['nazev']}")
                
    except Exception as e:
        logger.error(f"Chyba při načítání dat: {e}")

if __name__ == "__main__":
    main() 