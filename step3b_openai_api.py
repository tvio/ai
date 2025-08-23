#!/usr/bin/env python3
"""
Krok 3b: Extrakce informací z PDF dokumentů pomocí OpenAI API
Alternativa k Ollama s použitím OpenAI API
"""

import requests
import pg8000
import json
import time
from typing import List, Dict, Any, Optional
import logging
import pdfplumber
from openai import OpenAI
from io import BytesIO
from openai_config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_MAX_TOKENS, OPENAI_SEED

# Nastavení logování
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFExtractor:
    """Třída pro extrakci textu z PDF s OpenAI API"""
    
    def __init__(self, api_key: str):
        self.openai_client = OpenAI(api_key=api_key)
    
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
        """Extrahuje informace o léku pomocí OpenAI API"""
        try:
                        # Prompt pro OpenAI API
            prompt = f"""
            Analyzuj následující text z SPC (Souhrn údajů o přípravku) pro lék s kódem SÚKL: {kod_sukl}
            
            Extrahuj následující informace a vrať je v JSON formátu:
            
            {{
                "indikace": [""],
                "davkovani": [""],
          }}
            Text: {text[:2000]}
        """

            
            # Volání OpenAI API
            response = self.openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{
                    'role': 'user',
                    'content': prompt
                }],
                # temperature=0.0 není podporováno GPT-5-nano, používá výchozí 1.0
                response_format={"type": "json_object"},  # Zajišťuje JSON výstup
                seed=OPENAI_SEED
            )
            
            # Parsování JSON odpovědi
            try:
                content = response.choices[0].message.content
                if content is None:
                    logger.error(f"Prázdný obsah odpovědi pro {kod_sukl}")
                    return {}
                    
                result = json.loads(content)
                logger.info(f"Úspěšně extrahovány informace pro {kod_sukl}")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Chyba při parsování JSON odpovědi pro {kod_sukl}: {e}")
                logger.error(f"Odpověď: {content}")
                return {}
                
        except Exception as e:
            logger.error(f"Chyba při OpenAI API extrakci pro {kod_sukl}: {e}")
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
                            kod_sukl VARCHAR(20) REFERENCES leciva(kod_sukl) UNIQUE,
                            indikace TEXT[],
                            davkovani TEXT[],
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
                            kod_sukl, indikace, davkovani, extracted_text
                        ) VALUES (%s, %s, %s, %s)
                        ON CONFLICT (kod_sukl) DO UPDATE SET
                            indikace = EXCLUDED.indikace,
                            davkovani = EXCLUDED.davkovani,
                            extracted_text = EXCLUDED.extracted_text
                    """, (
                        kod_sukl,
                        extracted_info.get('indikace', []),
                        extracted_info.get('davkovani', []),
                        extracted_text[:1000]  # Omezíme délku uloženého textu
                    ))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Chyba při ukládání extrahovaných informací pro {kod_sukl}: {e}")
            return False
    


def main():
    """Hlavní funkce pro extrakci informací z PDF pomocí OpenAI API"""
    logger.info("🚀 Začínám extrakci informací z PDF dokumentů pomocí OpenAI API")
    
    # Inicializace
    extractor = PDFExtractor(OPENAI_API_KEY)
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
                        
                        # 2. OpenAI API extrakce informací
                        extracted_info = extractor.extract_medicine_info(text, kod_sukl)
                        if not extracted_info:
                            logger.warning(f"Prázdné extrahované informace pro {kod_sukl}")
                            continue
                        
                        # 3. Uložení do databáze
                        if db_manager.save_extracted_info(kod_sukl, extracted_info, text):
                            logger.info(f"✅ Informace uloženy pro {kod_sukl}")
                        else:
                            logger.error(f"❌ Chyba při ukládání pro {kod_sukl}")
                        
                        # Kratší pauza pro OpenAI API (rate limiting)
                        time.sleep(5)  # 5 sekund pauza mezi dotazy
                        
                    except Exception as e:
                        logger.error(f"Chyba při zpracování {kod_sukl}: {e}")
                        continue
                

                
    except Exception as e:
        logger.error(f"Chyba při načítání dat: {e}")

if __name__ == "__main__":
    main()
