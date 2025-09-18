from flask import Flask, request, jsonify
import json
import os
from datetime import datetime, timezone
import logging

app = Flask(__name__)

# Configuración
UPLOAD_SECRET = "clave_para_subir_archivos_2024"
LICENSES_DIR = "client_licenses"  # Directorio para almacenar licencias por cliente
GLOBAL_LICENSES_FILE = "global_licenses.json"

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear directorio de licencias si no existe
os.makedirs(LICENSES_DIR, exist_ok=True)

def load_json(file_path):
    """Cargar archivo JSON de forma segura"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return json.loads(content) if content else {}
        return {}
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return {}

def save_json(file_path, data):
    """Guardar archivo JSON de forma segura"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving {file_path}: {e}")
        return False

def get_client_licenses_file(discord_id):
    """Obtener la ruta del archivo de licencias de un cliente"""
    return os.path.join(LICENSES_DIR, f"client_{discord_id}.json")

@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que la API está funcionando"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "API de licencias funcionando correctamente"
    })

@app.route('/api/upload/<discord_id>', methods=['POST'])
def upload_client_licenses(discord_id):
    """
    Endpoint para subir las licencias de un cliente específico
    """
    try:
        # Verificar autorización
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer ') or auth_header[7:] != UPLOAD_SECRET:
            return jsonify({"error": "Unauthorized"}), 401
        
        # Obtener datos del request
        licenses_data = request.get_json()
        if not licenses_data:
            return jsonify({"error": "No data provided"}), 400
        
        # Guardar licencias del cliente
        client_file = get_client_licenses_file(discord_id)
        if save_json(client_file, licenses_data):
            logger.info(f"Licencias actualizadas para cliente {discord_id}")
            
            # También actualizar el archivo global
            update_global_licenses()
            
            return jsonify({
                "success": True,
                "message": f"Licencias actualizadas para Discord ID: {discord_id}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "licenses_count": len(licenses_data)
            })
        else:
            return jsonify({"error": "Failed to save licenses"}), 500
            
    except Exception as e:
        logger.error(f"Error in upload_client_licenses: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/licenses/<discord_id>', methods=['GET'])
def get_client_licenses(discord_id):
    """
    Endpoint para obtener las licencias de un cliente específico
    """
    try:
        client_file = get_client_licenses_file(discord_id)
        licenses = load_json(client_file)
        
        if licenses:
            return jsonify({
                "success": True,
                "discord_id": discord_id,
                "licenses": licenses,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "message": "No licenses found for this Discord ID"
            }), 404
            
    except Exception as e:
        logger.error(f"Error in get_client_licenses: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/licenses', methods=['GET'])
def get_all_licenses():
    """
    Endpoint para obtener todas las licencias (solo para administradores)
    """
    try:
        # Verificar autorización
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer ') or auth_header[7:] != UPLOAD_SECRET:
            return jsonify({"error": "Unauthorized"}), 401
        
        global_licenses = load_json(GLOBAL_LICENSES_FILE)
        
        return jsonify({
            "success": True,
            "licenses": global_licenses,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_licenses": len(global_licenses)
        })
        
    except Exception as e:
        logger.error(f"Error in get_all_licenses: {e}")
        return jsonify({"error": "Internal server error"}), 500

def update_global_licenses():
    """
    Actualizar el archivo global de licencias combinando todas las licencias de clientes
    """
    try:
        global_licenses = {}
        
        # Leer todas las licencias de clientes
        for filename in os.listdir(LICENSES_DIR):
            if filename.startswith('client_') and filename.endswith('.json'):
                client_file = os.path.join(LICENSES_DIR, filename)
                client_licenses = load_json(client_file)
                global_licenses.update(client_licenses)
        
        # Guardar archivo global
        save_json(GLOBAL_LICENSES_FILE, global_licenses)
        logger.info(f"Archivo global actualizado con {len(global_licenses)} licencias")
        
    except Exception as e:
        logger.error(f"Error updating global licenses: {e}")

@app.route('/api/sync', methods=['POST'])
def sync_all_licenses():
    """
    Endpoint para sincronizar todas las licencias
    """
    try:
        # Verificar autorización
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer ') or auth_header[7:] != UPLOAD_SECRET:
            return jsonify({"error": "Unauthorized"}), 401
        
        update_global_licenses()
        
        return jsonify({
            "success": True,
            "message": "Sincronización completada",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in sync_all_licenses: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    # Para desarrollo local
    app.run(debug=True, host="0.0.0.0", port=5000)