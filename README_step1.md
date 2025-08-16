# Krok 1: Základní práce s Ollama modelem

Tento krok demonstruje, jak používat lokální AI model (Ollama) v Pythonu.

## Co se naučíte

- ✅ Instalace a spuštění Ollama
- ✅ Komunikace s Ollama API z Pythonu
- ✅ Seznam dostupných modelů
- ✅ Generování textu pomocí lokálního modelu

## Instalace

### 1. Instalace Ollama
Stáhněte a nainstalujte Ollama z: https://ollama.ai/

### 2. Stažení modelu
```bash
# Stáhněte základní model
ollama pull llama2

# Nebo menší model
ollama pull mistral
```

### 3. Python závislosti
```bash
pip install -r requirements_step1.txt
```

## Použití

### Spuštění testu
```bash
python step1_ollama_basic.py
```

### Co skript dělá

1. **Test připojení** - Ověří, že Ollama běží
2. **Seznam modelů** - Zobrazí dostupné modely
3. **Test generování** - Vygeneruje text pomocí modelu

### Příklad výstupu
```
🤖 Ollama - Základní test
========================================
1. Test připojení k Ollama...
✅ Ollama je dostupné!

2. Dostupné modely:
   📋 llama2 (3.8 GB)

3. Test generování textu...
   Používám model: llama2
   Prompt: Napiš krátkou básničku o umělé inteligenci.
   ✅ Odpověď:
   [Generovaný text...]
```

## Další kroky

- **Krok 2**: Práce s PDF soubory
- **Krok 3**: Vytváření embeddingů
- **Krok 4**: Ukládání do databáze

## Řešení problémů

### Ollama není dostupné
- Zkontrolujte, že Ollama je nainstalováno
- Spusťte Ollama službu
- Zkontrolujte port 11434

### Žádné modely
```bash
ollama pull llama2
```

### Chyba připojení
- Zkontrolujte firewall
- Zkontrolujte, že Ollama běží na localhost:11434 