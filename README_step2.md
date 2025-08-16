# Krok 2: Stahování dat z SÚKL API

Tento krok demonstruje stahování dat z SÚKL API a ukládání do PostgreSQL databáze.

## Co se naučíte

- ✅ Komunikace s REST API
- ✅ Stahování PDF dokumentů
- ✅ Ukládání do PostgreSQL
- ✅ Zpracování velkých datových souborů
- ✅ Logování a error handling

## Instalace

### 1. PostgreSQL databáze
Ujistěte se, že máte PostgreSQL běžící na localhost:5432 s databází `test` a uživatelem `test/test`.

### 2. Python závislosti
```bash
pip install -r requirements_step2.txt
```

## Použití

### Spuštění skriptu
```bash
python step2_sukl_api.py
```

### Co skript dělá

1. **Stáhne seznam léků** z SÚKL API
2. **Získá detaily** pro každý lék
3. **Stáhne SPC dokumenty** (PDF)
4. **Uloží vše do PostgreSQL**

### Databázové schéma

**Tabulka `leciva`:**
- `kod_sukl` - Primární klíč
- `nazev` - Název léku
- `sila` - Síla léku
- `atc_kod` - ATC kód
- `ddd_mnozstvi` - DDD množství
- `registracni_cislo` - Registrační číslo
- A další metadata...

**Tabulka `dokumenty`:**
- `id` - Primární klíč
- `kod_sukl` - Reference na léky
- `dokument_id` - ID dokumentu z API
- `pdf_data` - Binární data PDF
- `pdf_size` - Velikost PDF

## API Endpoints

Skript používá tyto SÚKL API endpointy:

1. **Seznam léků**: `GET /lecive-pripravky`
2. **Detail léku**: `GET /lecive-pripravky/{kodSUKL}`
3. **Metadata dokumentů**: `GET /dokumenty-metadata/{kodSUKL}?typ=spc`
4. **Stažení PDF**: `GET /dokumenty/{id}`

## Konfigurace

### Databázové připojení
```python
DatabaseManager(
    host="localhost",
    port=5432,
    database="test",
    user="test",
    password="test"
)
```

### API parametry
```python
# Období pro stahování
period="2023.09"

# Typ dokumentů
doc_type="spc"  # SPC dokumenty
```

## Příklad výstupu

```
2024-01-15 10:30:00 - INFO - 🚀 Začínám stahování dat z SÚKL API
2024-01-15 10:30:05 - INFO - Stahuji seznam léků pro období 2023.09...
2024-01-15 10:30:08 - INFO - Načteno 15420 kódů léků
2024-01-15 10:30:08 - INFO - Testuji s prvních 10 léky
2024-01-15 10:30:08 - INFO - Zpracovávám 1/10: 0094156
2024-01-15 10:30:10 - INFO - ✅ Léky uložen: ABAKTAL
2024-01-15 10:30:10 - INFO -   📄 Stahuji dokument 80188: SPC221420.pdf
2024-01-15 10:30:12 - INFO -   ✅ Dokument uložen: 245760 bytes
...
2024-01-15 10:31:00 - INFO - ==================================================
2024-01-15 10:31:00 - INFO - 🎉 Stahování dokončeno!
2024-01-15 10:31:00 - INFO - ✅ Úspěšně uloženo léků: 10
2024-01-15 10:31:00 - INFO - 📄 Úspěšně uloženo dokumentů: 8
```

## Řešení problémů

### Chyba připojení k databázi
- Zkontrolujte, že PostgreSQL běží
- Ověřte přihlašovací údaje
- Zkontrolujte, že databáze `test` existuje

### Chyba API
- Zkontrolujte internetové připojení
- API může být dočasně nedostupné
- Zkuste později

### Timeout
- Zvýšte timeout v kódu
- Přidejte více pauz mezi požadavky
- Omezte počet současných požadavků

## Další kroky

- **Krok 3**: Vytváření embeddingů z PDF textu
- **Krok 4**: Sémantické vyhledávání v dokumentech
- **Krok 5**: Webové rozhraní pro vyhledávání 