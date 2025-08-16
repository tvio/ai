#!/usr/bin/env python3
"""
Krok 2: Stahování dat z SÚKL API a ukládání do PostgreSQL
"""

import requests
import pg8000
import json
import time
from typing import List, Dict, Any
import logging

# Nastavení logování
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SUKLAPIClient:
    """Klient pro komunikaci s SÚKL API"""
    
    def __init__(self, base_url: str = "https://prehledy.sukl.cz/dlp/v1"):
        self.base_url = base_url
        self.session = requests.Session()
   
    def get_medicines_list(self, period: str = "2025.08", ) -> List[str]:
        """Získá seznam kódů léků"""
        params = f"obdobi={period}&uvedeneCeny=false&typSeznamu=dlpo"
        url = f"{self.base_url}/lecive-pripravky?{params}"
        logger.info(f"URL pro seznam kodu: {url}")
        try:
            logger.info(f"Stahuji seznam léků pro období {period}...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Status kód: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            data = response.json()
           
            codes = data if isinstance(data, list) else []
            
            logger.info(f"Načteno {len(codes)} kódů léků")
            return codes
            
        except Exception as e:
            logger.error(f"Chyba při stahování seznamu léků: {e}")
            return []
    
    def get_medicine_detail(self, kod_sukl: str) -> Dict[str, Any]:
        """Získá detail léku podle kódu SÚKL"""
        url = f"{self.base_url}/lecive-pripravky/{kod_sukl}"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Chyba při stahování detailu léku {kod_sukl}: {e}")
            return {}
    
    def get_documents_metadata(self, kod_sukl: str, doc_type: str = "spc") -> List[Dict[str, Any]]:
        """Získá metadata dokumentů pro léky"""
        url = f"{self.base_url}/dokumenty-metadata/{kod_sukl}"
        params = {'typ': doc_type}
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            # Pokud je to jeden objekt, převedeme na list
            if isinstance(data, dict):
                return [data]
            elif isinstance(data, list):
                return data
            else:
                return []
                
        except Exception as e:
            logger.error(f"Chyba při stahování metadat dokumentů pro {kod_sukl}: {e}")
            return []
    
    def download_document(self, kod_sukl: str, doc_type: str = "spc", is_eu_registration: bool = False, max_retries: int = 3) -> bytes:
        """Stáhne PDF dokument podle kódu SÚKL a typu dokumentu"""
        url = f"{self.base_url}/dokumenty/{kod_sukl}/{doc_type}"
        
        # Delší pauza pro EU registrace (EMA server)
        if is_eu_registration:
            logger.info(f"  ⚠️  EU registrace - používám delší pauzu pro EMA server")
            time.sleep(3)  # 3 sekundy pro EMA
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=60)
                response.raise_for_status()
                
                return response.content
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Too Many Requests
                    wait_time = (2 ** attempt) * 5  # Exponential backoff: 5, 10, 20 sekund
                    logger.warning(f"  ⚠️  429 Too Many Requests - čekám {wait_time}s (pokus {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Příliš mnoho požadavků i po {max_retries} pokusech")
                        return b""
                else:
                    raise
                    
            except Exception as e:
                logger.error(f"Chyba při stahování dokumentu {kod_sukl}/{doc_type}: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"  🔄 Opakuji za 2 sekundy (pokus {attempt + 2}/{max_retries})")
                    time.sleep(2)
                    continue
                return b""
        
        return b""

class DatabaseManager:
    """Správce databáze PostgreSQL"""
    
    def __init__(self, host: str = "localhost", port: int = 5432, 
                 database: str = "test", user: str = "test", password: str = "test"):
        self.connection_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
        self.init_database()
    
    def init_database(self):
        """Inicializuje databázi a vytvoří tabulky"""
        try:
            with pg8000.connect(**self.connection_params) as conn:
                with conn.cursor() as cursor:
                    
                    # Smazat existující tabulky pro testování
                    cursor.execute("DROP TABLE IF EXISTS dokumenty CASCADE")
                    cursor.execute("DROP TABLE IF EXISTS leciva CASCADE")
                    conn.commit()
                    logger.info("Existující tabulky smazány")
                    
                    # Tabulka léků - vše jako string pro testování
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS leciva (
                            kod_sukl VARCHAR(20) PRIMARY KEY,
                            nazev VARCHAR(500),
                            sila VARCHAR(100),
                            lekova_forma VARCHAR(100),
                            baleni VARCHAR(50),
                            cesta VARCHAR(50),
                            doplnek TEXT,
                            obal VARCHAR(50),
                            drzitel VARCHAR(100),
                            zeme_drzitele VARCHAR(50),
                            stav_registrace VARCHAR(10),
                            atc_kod VARCHAR(20),
                            registracni_cislo VARCHAR(100),
                            ddd_mnozstvi VARCHAR(20),
                            ddd_jednotka VARCHAR(10),
                            ddd_baleni VARCHAR(20),
                            zpusob_vydeje VARCHAR(10),
                            expirace VARCHAR(20),
                            expirace_jednotka VARCHAR(10),
                            registrovany_nazev VARCHAR(500),
                            ochranne_prvky VARCHAR(10),
                            jazyk_obalu VARCHAR(10),
                            datum_registrace VARCHAR(20),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Tabulka dokumentů
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS dokumenty (
                            id SERIAL PRIMARY KEY,
                            kod_sukl VARCHAR(20) REFERENCES leciva(kod_sukl),
                            dokument_id VARCHAR(20),
                            typ VARCHAR(50),
                            nazev VARCHAR(500),
                            pdf_data BYTEA,
                            pdf_size INTEGER,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(kod_sukl, dokument_id)
                        )
                    """)
                    
                    conn.commit()
                    logger.info("Databáze inicializována")
                    
        except Exception as e:
            logger.error(f"Chyba při inicializaci databáze: {e}")
            raise
    
    def save_medicine(self, medicine_data: Dict[str, Any]) -> bool:
        """Uloží data léku do databáze"""
        try:
            with pg8000.connect(**self.connection_params) as conn:
                with conn.cursor() as cursor:
                    
                    cursor.execute("""
                        INSERT INTO leciva (
                            kod_sukl, nazev, sila, lekova_forma, baleni, cesta,
                            doplnek, obal, drzitel, zeme_drzitele, stav_registrace,
                            atc_kod, registracni_cislo, ddd_mnozstvi, ddd_jednotka,
                            ddd_baleni, zpusob_vydeje, expirace, expirace_jednotka,
                            registrovany_nazev, ochranne_prvky, jazyk_obalu, datum_registrace
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (kod_sukl) DO UPDATE SET
                            nazev = EXCLUDED.nazev,
                            sila = EXCLUDED.sila,
                            lekova_forma = EXCLUDED.lekova_forma,
                            baleni = EXCLUDED.baleni,
                            cesta = EXCLUDED.cesta,
                            doplnek = EXCLUDED.doplnek,
                            obal = EXCLUDED.obal,
                            drzitel = EXCLUDED.drzitel,
                            zeme_drzitele = EXCLUDED.zeme_drzitele,
                            stav_registrace = EXCLUDED.stav_registrace,
                            atc_kod = EXCLUDED.atc_kod,
                            registracni_cislo = EXCLUDED.registracni_cislo,
                            ddd_mnozstvi = EXCLUDED.ddd_mnozstvi,
                            ddd_jednotka = EXCLUDED.ddd_jednotka,
                            ddd_baleni = EXCLUDED.ddd_baleni,
                            zpusob_vydeje = EXCLUDED.zpusob_vydeje,
                            expirace = EXCLUDED.expirace,
                            expirace_jednotka = EXCLUDED.expirace_jednotka,
                            registrovany_nazev = EXCLUDED.registrovany_nazev,
                            ochranne_prvky = EXCLUDED.ochranne_prvky,
                            jazyk_obalu = EXCLUDED.jazyk_obalu,
                            datum_registrace = EXCLUDED.datum_registrace
                    """, (
                        str(medicine_data.get('kodSUKL', '')),
                        str(medicine_data.get('nazev', '')),
                        str(medicine_data.get('sila', '')),
                        str(medicine_data.get('lekovaFormaKod', '')),
                        str(medicine_data.get('baleni', '')),
                        str(medicine_data.get('cestaKod', '')),
                        str(medicine_data.get('doplnek', '')),
                        str(medicine_data.get('obalKod', '')),
                        str(medicine_data.get('drzitelKod', '')),
                        str(medicine_data.get('zemeDrziteleKod', '')),
                        str(medicine_data.get('stavRegistraceKod', '')),
                        str(medicine_data.get('ATCkod', '')),
                        str(medicine_data.get('registracniCislo', '')),
                        str(medicine_data.get('dddMnozstvi', '')),
                        str(medicine_data.get('dddMnozstviJednotka', '')),
                        str(medicine_data.get('dddBaleni', '')),
                        str(medicine_data.get('zpusobVydejeKod', '')),
                        str(medicine_data.get('expirace', '')),
                        str(medicine_data.get('expiraceJednotka', '')),
                        str(medicine_data.get('registrovanyNazevLP', '')),
                        str(medicine_data.get('ochrannePrvky', '')),
                        str(medicine_data.get('jazykObalu', '')),
                        str(medicine_data.get('datumRegistrace', ''))
                    ))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Chyba při ukládání léku {medicine_data.get('kodSUKL')}: {e}")
            return False
    
    def save_document(self, kod_sukl: str, document_data: Dict[str, Any], pdf_content: bytes) -> bool:
        """Uloží dokument do databáze"""
        try:
            with pg8000.connect(**self.connection_params) as conn:
                with conn.cursor() as cursor:
                    
                    cursor.execute("""
                        INSERT INTO dokumenty (
                            kod_sukl, dokument_id, typ, nazev, pdf_data, pdf_size
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (kod_sukl, dokument_id) DO UPDATE SET
                            typ = EXCLUDED.typ,
                            nazev = EXCLUDED.nazev,
                            pdf_data = EXCLUDED.pdf_data,
                            pdf_size = EXCLUDED.pdf_size
                    """, (
                        kod_sukl,
                        str(document_data.get('id', '')),
                        document_data.get('typ', 'spc'),
                        document_data.get('nazev', ''),
                        pdf_content,
                        len(pdf_content)
                    ))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Chyba při ukládání dokumentu pro {kod_sukl}: {e}")
            return False

def main():
    """Hlavní funkce pro stahování dat"""
    logger.info("🚀 Začínám stahování dat z SÚKL API")
    
    # Konfigurace
    SKIP_EU_REGISTRATIONS = True  # Nastavte na False pokud chcete stahovat i EU registrace
    
    # Inicializace klientů
    api_client = SUKLAPIClient()
    db_manager = DatabaseManager()
    
    # 1. Získání seznamu léků
    medicine_codes = api_client.get_medicines_list()
    
    if not medicine_codes:
        logger.error("Nepodařilo se získat seznam léků")
        return
    
    logger.info(f"Načteno {len(medicine_codes)} léků k zpracování")
    
    # Nastavení pro test
    TARGET_MEDICINES = 10  # Počet léčiv s PDF, které chceme získat
    MAX_ATTEMPTS = 5000      # Maximální počet pokusů (aby se nám nezacyklilo)
    
    success_count = 0
    document_count = 0
    skipped_eu_count = 0
    processed_count = 0
    
    logger.info(f"Cíl: získat {TARGET_MEDICINES} léčiv s PDF dokumenty (max {MAX_ATTEMPTS} pokusů)")
    
    for kod_sukl in medicine_codes:
        processed_count += 1
        logger.info(f"Zpracovávám {processed_count}: {kod_sukl} (úspěšně: {success_count}/{TARGET_MEDICINES})")
        
        # Kontrola ukončení - buď dosáhli cíle nebo vyčerpali pokusy
        if success_count >= TARGET_MEDICINES:
            logger.info(f"🎯 Dosažen cíl {TARGET_MEDICINES} léčiv s PDF!")
            break
        
        if processed_count > MAX_ATTEMPTS:
            logger.warning(f"⚠️  Dosažen limit {MAX_ATTEMPTS} pokusů")
            break
        
        try:
            # 2. Získání detailu léku
            medicine_detail = api_client.get_medicine_detail(kod_sukl)
            
            if not medicine_detail:
                logger.warning(f"  ⚠️  Nepodařilo se získat detail léku {kod_sukl}")
                continue
            
            # Kontrola EU registrace
            registracni_cislo = medicine_detail.get('registracniCislo', '')
            is_eu_registration = str(registracni_cislo).startswith('EU')
            
            # Přeskočení celého léčiva pokud je EU registrace a nechceme je
            if is_eu_registration and SKIP_EU_REGISTRATIONS:
                logger.info(f"  ⏭️  Přeskakuji celé léčivo s EU registrací: {registracni_cislo} ({medicine_detail.get('nazev', kod_sukl)})")
                skipped_eu_count += 1
                continue
            
            if is_eu_registration:
                logger.info(f"  🇪🇺 EU registrace: {registracni_cislo}")
            
            # 3. Stahování SPC dokumentu nejdříve
            logger.info(f"  📄 Stahuji SPC dokument pro {kod_sukl}")
            
            pdf_content = api_client.download_document(kod_sukl, "spc", is_eu_registration)
            if not pdf_content:
                logger.warning(f"  ⚠️  Prázdný SPC dokument pro {kod_sukl} - přeskakuji")
                continue
            
            # 4. Uložení léčiva do databáze (pouze pokud máme PDF)
            if not db_manager.save_medicine(medicine_detail):
                logger.error(f"❌ Chyba při ukládání léčiva: {kod_sukl}")
                continue
            
            # 5. Uložení PDF dokumentu
            doc_data = {
                'id': kod_sukl,
                'nazev': f'SPC_{kod_sukl}.pdf',
                'typ': 'spc'
            }
            if db_manager.save_document(kod_sukl, doc_data, pdf_content):
                success_count += 1
                document_count += 1
                logger.info(f"✅ Léčivo a PDF uloženo: {medicine_detail.get('nazev', kod_sukl)} ({len(pdf_content)} bytes)")
            else:
                logger.error(f"  ❌ Chyba při ukládání SPC dokumentu")
            
            # Pauza mezi požadavky - kratší pro lokální SÚKL, delší už je v download_document pro EMA
            time.sleep(0.5 if not is_eu_registration else 1)
            
        except Exception as e:
            logger.error(f"Chyba při zpracování {kod_sukl}: {e}")
            continue
    
    logger.info("=" * 50)
    logger.info(f"🎉 Stahování dokončeno!")
    logger.info(f"📊 Statistiky:")
    logger.info(f"   • Zpracováno léčiv: {processed_count}")
    logger.info(f"   • Úspěšně uloženo léčiv s PDF: {success_count}")
    logger.info(f"   • Úspěšně uloženo dokumentů: {document_count}")
    if skipped_eu_count > 0:
        logger.info(f"   • Přeskočeno EU registrací: {skipped_eu_count}")
    logger.info(f"ℹ️  Pro stahování EU registrací nastavte SKIP_EU_REGISTRATIONS = False")

if __name__ == "__main__":
    main() 