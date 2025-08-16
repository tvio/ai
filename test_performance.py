#!/usr/bin/env python3
"""
Test výkonu různých Ollama modelů
"""

import requests
import time
import psutil
import os

def get_system_info():
    """Získá informace o systému"""
    cpu_count = psutil.cpu_count()
    memory_gb = psutil.virtual_memory().total / (1024**3)
    
    # Kontrola GPU (jednoduchá)
    gpu_available = False
    try:
        import torch
        gpu_available = torch.cuda.is_available()
    except:
        pass
    
    return {
        'cpu_cores': cpu_count,
        'memory_gb': round(memory_gb, 1),
        'gpu_available': gpu_available
    }

def test_model_performance(model_name, prompt="Napiš krátkou básničku o umělé inteligenci."):
    """Otestuje výkon modelu"""
    print(f"\n🧪 Testuji model: {model_name}")
    print("-" * 40)
    
    # Měření paměti před
    memory_before = psutil.virtual_memory().used / (1024**3)
    
    # Měření času
    start_time = time.time()
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False
            },
            timeout=120  # 2 minuty timeout
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Měření paměti po
        memory_after = psutil.virtual_memory().used / (1024**3)
        memory_used = memory_after - memory_before
        
        if response.status_code == 200:
            data = response.json()
            response_text = data.get('response', '')
            response_length = len(response_text)
            
            print(f"✅ Úspěch!")
            print(f"⏱️  Čas: {duration:.2f} sekund")
            print(f"💾 Paměť: +{memory_used:.1f} GB")
            print(f"📝 Délka odpovědi: {response_length} znaků")
            print(f"🚀 Rychlost: {response_length/duration:.0f} znaků/sekundu")
            
            # Ukázka odpovědi
            preview = response_text[:100] + "..." if len(response_text) > 100 else response_text
            print(f"📄 Ukázka: {preview}")
            
            return {
                'success': True,
                'duration': duration,
                'memory_used': memory_used,
                'response_length': response_length
            }
        else:
            print(f"❌ Chyba: {response.status_code}")
            return {'success': False}
            
    except requests.exceptions.Timeout:
        print("❌ Timeout - model je příliš pomalý")
        return {'success': False, 'timeout': True}
    except Exception as e:
        print(f"❌ Chyba: {e}")
        return {'success': False}

def main():
    print("🖥️  Test výkonu Ollama modelů")
    print("=" * 50)
    
    # Informace o systému
    system = get_system_info()
    print(f"💻 CPU: {system['cpu_cores']} jader")
    print(f"💾 RAM: {system['memory_gb']} GB")
    print(f"🎮 GPU: {'Dostupné' if system['gpu_available'] else 'Nedostupné'}")
    
    # Doporučení podle systému
    if system['memory_gb'] < 8:
        print("\n⚠️  Máte méně než 8 GB RAM - doporučuji menší modely")
        recommended_models = ['phi', 'gemma2']
    elif system['memory_gb'] < 16:
        print("\n⚠️  Máte 8-16 GB RAM - střední modely")
        recommended_models = ['gemma2', 'llama2']
    else:
        print("\n✅ Máte dostatek RAM - můžete zkusit větší modely")
        recommended_models = ['llama2', 'mistral', 'gemma2']
    
    # Test dostupných modelů
    print(f"\n🔍 Testuji doporučené modely: {', '.join(recommended_models)}")
    
    results = {}
    
    for model in recommended_models:
        result = test_model_performance(model)
        results[model] = result
        
        if not result.get('success'):
            print(f"💡 Zkuste: ollama pull {model}")
    
    # Shrnutí
    print("\n" + "=" * 50)
    print("📊 Shrnutí výsledků:")
    
    successful_models = [m for m, r in results.items() if r.get('success')]
    
    if successful_models:
        print("✅ Funkční modely:")
        for model in successful_models:
            result = results[model]
            print(f"   {model}: {result['duration']:.1f}s, +{result['memory_used']:.1f}GB RAM")
        
        # Nejlepší model
        best_model = min(successful_models, 
                        key=lambda m: results[m]['duration'])
        print(f"\n🏆 Doporučený model: {best_model}")
    else:
        print("❌ Žádný model nefunguje")
        print("💡 Zkuste:")
        print("   1. ollama pull phi")
        print("   2. ollama pull gemma2")

if __name__ == "__main__":
    main() 