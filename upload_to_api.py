import requests
import json
import os
from datetime import datetime

# Configuración de la API
API_BASE_URL = "https://flowshop2kee.pythonanywhere.com"  # Tu URL de PythonAnywhere
UPLOAD_SECRET = "clave_para_subir_archivos_2024"  # Debe coincidir con la API
TIMEOUT = 30

def upload_client_licenses(discord_id, licenses_data):
    """
    Subir las licencias de un cliente específico a la API
    """
    try:
        url = f"{API_BASE_URL}/api/upload/{discord_id}"
        headers = {
            'Authorization': f'Bearer {UPLOAD_SECRET}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            url, 
            json=licenses_data, 
            headers=headers, 
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Licencias subidas exitosamente para Discord ID: {discord_id}")
            print(f"   Timestamp: {result.get('timestamp', 'N/A')}")
            return True
        else:
            print(f"❌ Error al subir licencias para Discord ID {discord_id}")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión al subir licencias para Discord ID {discord_id}: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado al subir licencias para Discord ID {discord_id}: {str(e)}")
        return False

def sync_all_clients_to_api(global_licenses_file="licenses.json"):
    """
    Sincronizar todas las licencias del archivo global a la API,
    organizándolas por cliente individual
    """
    try:
        # Verificar que el archivo global existe
        if not os.path.exists(global_licenses_file):
            print(f"❌ Archivo global de licencias no encontrado: {global_licenses_file}")
            return False
        
        # Cargar licencias globales
        with open(global_licenses_file, 'r', encoding='utf-8') as f:
            global_licenses = json.load(f)
        
        if not global_licenses:
            print("⚠️ No hay licencias en el archivo global")
            return True
        
        # Organizar licencias por Discord ID
        clients_licenses = {}
        for license_key, license_data in global_licenses.items():
            discord_id = str(license_data.get("discord_id", ""))
            if discord_id and discord_id != "":
                if discord_id not in clients_licenses:
                    clients_licenses[discord_id] = {}
                clients_licenses[discord_id][license_key] = license_data
        
        # Subir licencias para cada cliente
        success_count = 0
        total_clients = len(clients_licenses)
        
        print(f"🔄 Sincronizando licencias para {total_clients} clientes...")
        
        for discord_id, client_licenses in clients_licenses.items():
            print(f"\n📤 Subiendo licencias para Discord ID: {discord_id}")
            print(f"   Licencias: {len(client_licenses)}")
            
            if upload_client_licenses(discord_id, client_licenses):
                success_count += 1
            else:
                print(f"   ❌ Falló la subida para Discord ID: {discord_id}")
        
        print(f"\n📊 Resumen de sincronización:")
        print(f"   ✅ Exitosos: {success_count}/{total_clients}")
        print(f"   ❌ Fallidos: {total_clients - success_count}/{total_clients}")
        
        return success_count == total_clients
        
    except json.JSONDecodeError as e:
        print(f"❌ Error al leer el archivo JSON: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado durante la sincronización: {str(e)}")
        return False

def test_api_connection():
    """
    Probar la conexión con la API
    """
    try:
        url = f"{API_BASE_URL}/api/health"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Conexión con la API exitosa")
            print(f"   Status: {data.get('status', 'N/A')}")
            print(f"   Timestamp: {data.get('timestamp', 'N/A')}")
            return True
        else:
            print(f"❌ Error de conexión con la API: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error al conectar con la API: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Script de sincronización con API de PythonAnywhere")
    print("=" * 50)
    
    # Probar conexión
    print("1. Probando conexión con la API...")
    if not test_api_connection():
        print("❌ No se pudo conectar con la API. Verifica la configuración.")
        exit(1)
    
    # Sincronizar todas las licencias
    print("\n2. Sincronizando todas las licencias...")
    if sync_all_clients_to_api():
        print("\n🎉 ¡Sincronización completada exitosamente!")
    else:
        print("\n❌ La sincronización falló. Revisa los errores anteriores.")
        exit(1)