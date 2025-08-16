#!/usr/bin/env python3
"""
Krok 1: Základní práce s Ollama modelem v Pythonu
"""

import requests
import json
from typing import List, Dict, Any

class OllamaClient:
    """Jednoduchý klient pro komunikaci s Ollama"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
    
    def list_models(self) -> List[Dict[str, Any]]:
        """Vrátí seznam dostupných modelů"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return data.get('models', [])
            else:
                print(f"Chyba při získávání modelů: {response.status_code}")
                return []
        except Exception as e:
            print(f"Chyba připojení k Ollama: {e}")
            return []
    
    def generate_text(self, model: str, prompt: str, system: str = None) -> str:
        """Vygeneruje text pomocí zadaného modelu"""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        if system:
            payload["system"] = system
        
        try:
            # Kratší timeout pro rychlejší testy
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=30  # 30 sekund místo 60
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('response', '')
            else:
                print(f"Chyba při generování: {response.status_code}")
                return ""
                
        except requests.exceptions.Timeout:
            print(f"❌ Timeout - model {model} je příliš pomalý")
            return ""
        except Exception as e:
            print(f"Chyba při komunikaci s modelem: {e}")
            return ""
    
    def test_connection(self) -> bool:
        """Otestuje připojení k Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

def main():
    print("🤖 Ollama - Základní test")
    print("=" * 40)
    
    # Vytvoření klienta
    client = OllamaClient()
    
    # Test připojení
    print("1. Test připojení k Ollama...")
    if client.test_connection():
        print("✅ Ollama je dostupné!")
    else:
        print("❌ Ollama není dostupné!")
        print("💡 Ujistěte se, že:")
        print("   - Ollama je nainstalováno")
        print("   - Ollama služba běží")
        print("   - Port 11434 je dostupný")
        return
    
    # Seznam modelů
    print("\n2. Dostupné modely:")
    models = client.list_models()
    if models:
        for model in models:
            print(f"   📋 {model['name']} ({model.get('size', 'N/A')} MB)")
    else:
        print("   ⚠️  Žádné modely nejsou staženy")
        print("   💡 Doporučené rychlé modely pro CPU:")
        print("      ollama pull phi3:mini        # 2.3GB - nejrychlejší")
        print("      ollama pull gemma2:2b        # 1.6GB - velmi rychlý")
        print("      ollama pull qwen2:1.5b       # 934MB - nejmenší")
        return
    
    # Test generování textu - rychlý test
    print("\n3. Rychlý test generování textu...")
    
    # Vybereme nejmenší dostupný model
    if models:
        # Seřadíme modely podle velikosti (předpokládáme, že menší = rychlejší)
        models.sort(key=lambda x: x.get('size', float('inf')))
        model_name = models[0]['name']
        print(f"   Používám nejmenší model: {model_name}")
        
        # Krátký test
        prompt = "Ahoj, jak se máš?"
        print(f"   Prompt: {prompt}")
        print("   ⏳ Čekám na odpověď (max 30 sekund)...")
        
        response = client.generate_text(model_name, prompt)
        if response:
            print("   ✅ Odpověď:")
            print(f"   {response}")
        else:
            print("   ❌ Chyba při generování nebo timeout")
            print("   💡 Zkuste menší model: ollama pull phi")
    else:
        print("   ⚠️  Žádné modely k testování")

if __name__ == "__main__":
    main() 