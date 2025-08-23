# OpenAI API Setup

## Konfigurace

1. **Vytvořte soubor `openai_config.py`** s vaším API klíčem:

```python
# OpenAI API konfigurace
OPENAI_API_KEY = "váš-api-klíč-zde"
OPENAI_MODEL = "gpt-5-nano"
OPENAI_MAX_TOKENS = 800
OPENAI_SEED = 42
```

2. **NIKDY necommitujte `openai_config.py` do gitu!**
   - Soubor je již v `.gitignore`
   - Obsahuje citlivé informace

## Bezpečnost

- ✅ **Soubor `openai_config.py` je v `.gitignore`**
- ✅ **API klíč není v hlavním kódu**
- ✅ **Konfigurace je centralizovaná**

## Použití

```python
from openai_config import OPENAI_API_KEY, OPENAI_MODEL

# Automaticky načte vaši konfiguraci
extractor = PDFExtractor(OPENAI_API_KEY)
```

## Poznámky

- Pro produkci použijte environment variables
- API klíč je citlivý - chraňte ho
- Model `gpt-5-nano` je nejlevnější dostupný
