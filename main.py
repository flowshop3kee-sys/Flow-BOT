import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import json
import random
import string
from datetime import datetime, timedelta, timezone
import aiohttp
import asyncio

# Importar funciones de sincronización con API
from upload_to_api import upload_client_licenses, sync_all_clients_to_api, test_api_connection

# Importar configuración desde archivo separado
from config import BOT_TOKEN, GUILD_ID, AUTHORIZED_USERS, WEBHOOK_URL, LICENSE_FILE

# Importar keep-alive para hosting en la nube
from keep_alive import keep_alive

# --- CLIENT LICENSE FUNCTIONS ---
def get_client_license_file(discord_id):
    """Obtiene el nombre del archivo de licencias específico para un cliente"""
    return f"client_licenses_{discord_id}.json"

def save_client_licenses(discord_id, licenses_data):
    """Guarda las licencias específicas de un cliente"""
    client_file = get_client_license_file(discord_id)
    save_json(client_file, licenses_data)

def update_client_license_files():
    """
    Actualiza todos los archivos de licencias de clientes basándose en el archivo global.
    Debe llamarse cada vez que se modifica el archivo global de licencias.
    """
    try:
        licenses = load_json(LICENSE_FILE)
        
        # Agrupar licencias por discord_id
        client_groups = {}
        for key, license_data in licenses.items():
            discord_id = license_data.get("discord_id")
            if discord_id is not None:  # Solo incluir licencias que tienen discord_id asignado
                discord_id = str(discord_id)
                if discord_id not in client_groups:
                    client_groups[discord_id] = {}
                client_groups[discord_id][key] = license_data
        
        # Crear/actualizar archivos individuales para cada cliente
        for discord_id, client_licenses in client_groups.items():
            save_client_licenses(discord_id, client_licenses)
            
    except Exception as e:
        print(f"❌ Error actualizando archivos de cliente: {e}")

def save_json_with_client_sync(file, data):
    """
    Guarda el archivo JSON, sincroniza los archivos de cliente y sube a la API de forma asíncrona
    """
    save_json(file, data)
    if file == LICENSE_FILE:
        update_client_license_files()
        # Programar sincronización con la API de forma asíncrona para evitar interferir con las interacciones
        try:
            # Usar asyncio para ejecutar la sincronización en segundo plano
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Si ya hay un loop corriendo, programar la tarea
                asyncio.create_task(sync_api_background())
            else:
                # Si no hay loop, ejecutar directamente
                print("🔄 Sincronizando con la API...")
                sync_all_clients_to_api(LICENSE_FILE)
                print("✅ Sincronización con API completada")
        except Exception as e:
            print(f"⚠️ Error al sincronizar con la API: {e}")
            # No fallar si la API no está disponible, solo mostrar advertencia

async def sync_api_background():
    """
    Función asíncrona para sincronizar con la API en segundo plano
    """
    try:
        print("🔄 Sincronizando con la API...")
        # Ejecutar en un thread separado para no bloquear el loop principal
        import asyncio
        import concurrent.futures
        
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            await loop.run_in_executor(executor, sync_all_clients_to_api, LICENSE_FILE)
        print("✅ Sincronización con API completada")
    except Exception as e:
        print(f"⚠️ Error al sincronizar con la API: {e}")

# --- JSON Handling ---
def load_json(file):
    try:
        with open(file, "r", encoding='utf-8') as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    except FileNotFoundError:
        print(f"⚠️ Warning: {file} not found. Creating new file.")
        return {}
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in {file}: {e}")
        return {}
    except Exception as e:
        print(f"❌ Error loading {file}: {e}")
        return {}

def save_json(file, data):
    try:
        with open(file, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Error saving {file}: {e}")
        raise

# --- License Functions ---
def generate_simple_key(prefix="FLOW", duration="1WEEK"):
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{duration}-{suffix}"

def create_license(duration_str="1WEEK"):
    licenses = load_json(LICENSE_FILE)
    key = generate_simple_key(duration=duration_str)
    licenses[key] = {
        "type": duration_str,
        "redeemed": False,
        "discord_id": None,
        "hwid": None,  # Hardware ID for anti-sharing
        "active": True,
        "online": False,
        "expires": None
    }
    save_json_with_client_sync(LICENSE_FILE, licenses)
    return key

def check_license(key):
    licenses = load_json(LICENSE_FILE)
    if key not in licenses:
        return False, "License not found", None
    
    lic = licenses[key]
    if not lic.get("active", True):
        return False, "License revoked", None
    
    # Check if license has expired
    expires = lic.get("expires")
    if expires and expires != "Lifetime":
        try:
            expiry_date = datetime.fromisoformat(expires.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expiry_date:
                return False, "License has expired", None
        except (ValueError, TypeError):
            pass  # Invalid date format, continue without expiry check
    
    # Retornar información completa de la licencia
    license_info = {
        "redeemed": lic.get("redeemed", False),
        "discord_id": lic.get("discord_id"),
        "redeem_time": lic.get("redeem_time"),
        "type": lic.get("type", "N/A"),
        "expires": lic.get("expires"),
        "active": lic.get("active", True),
        "online": lic.get("online", False)
    }
    
    status_msg = f"{'Already redeemed' if lic.get('redeemed', False) else 'Available for redeem'} (type: {lic.get('type','N/A')})"
    return True, status_msg, license_info

async def create_license_embed(key, license_info, interaction_client):
    """Crea un embed con información detallada de la licencia"""
    embed = discord.Embed(
        title="🔑 License Information",
        color=0xffa500,  # Naranja para todos los embeds de check_license
        timestamp=datetime.now(timezone.utc)
    )
    
    # Información básica de la licencia
    embed.add_field(
        name="📋 Status", 
        value="✅ Redeemed" if license_info["redeemed"] else "⏳ Available", 
        inline=True
    )
    embed.add_field(
        name="🏷️ Type", 
        value=license_info["type"], 
        inline=True
    )
    
    # Si está redimida, mostrar información del usuario
    if license_info["redeemed"] and license_info["discord_id"]:
        try:
            # Obtener información del usuario que redimió la licencia
            user = await interaction_client.fetch_user(license_info["discord_id"])
            
            embed.add_field(
                name="👤 Redeemed by", 
                value=f"{user.mention}\n**ID:** {user.id}\n**Username:** {user.name}", 
                inline=False
            )
            
            # Agregar foto de perfil
            embed.set_thumbnail(url=user.display_avatar.url)
            
            # Fecha de redeem
            if license_info["redeem_time"]:
                try:
                    redeem_date = datetime.fromisoformat(license_info["redeem_time"].replace('Z', '+00:00'))
                    formatted_date = redeem_date.strftime("%d/%m/%Y at %H:%M UTC")
                    embed.add_field(
                        name="📅 Redeem Date", 
                        value=formatted_date, 
                        inline=True
                    )
                except (ValueError, TypeError):
                    embed.add_field(
                        name="📅 Redeem Date", 
                        value="Unknown", 
                        inline=True
                    )
        except discord.NotFound:
            embed.add_field(
                name="👤 Redeemed by", 
                value=f"**ID:** {license_info['discord_id']}\n*User not found*", 
                inline=False
            )
        except Exception as e:
            print(f"Error fetching user info: {e}")
            embed.add_field(
                name="👤 Redeemed by", 
                value=f"**ID:** {license_info['discord_id']}", 
                inline=False
            )
    
    # Información de expiración
    if license_info["expires"]:
        if license_info["expires"] == "Lifetime":
            embed.add_field(
                name="⏰ Expires", 
                value="♾️ Lifetime", 
                inline=True
            )
        else:
            try:
                expire_date = datetime.fromisoformat(license_info["expires"].replace('Z', '+00:00'))
                formatted_expire = expire_date.strftime("%d/%m/%Y at %H:%M UTC")
                embed.add_field(
                    name="⏰ Expires", 
                    value=formatted_expire, 
                    inline=True
                )
            except (ValueError, TypeError):
                embed.add_field(
                    name="⏰ Expires", 
                    value="Unknown", 
                    inline=True
                )
    
    embed.set_footer(text=f"License Key: {key[:8]}...")
    return embed

def redeem_license(key, discord_id):
    licenses = load_json(LICENSE_FILE)
    if key not in licenses:
        return False, "License not found"

    lic = licenses[key]
    if not lic.get("active", True):
        return False, "License revoked"

    # --- ANTI-SHARING ---
    if lic.get("redeemed", False) and lic.get("discord_id") != discord_id:
        return False, "License already redeemed by another user"
    if lic.get("redeemed", False) and lic.get("discord_id") == discord_id:
        return False, "You have already redeemed this license"

    lic["redeemed"] = True
    lic["online"] = True
    lic["discord_id"] = discord_id
    lic["redeem_time"] = datetime.now(timezone.utc).isoformat()

    type_to_days = {
        "1DAY": 1,
        "3DAYS": 3,
        "7DAYS": 7,
        "1WEEK": 7,
        "1MONTH": 30,
        "LIFETIME": 0
    }
    days = type_to_days.get(lic.get("type"), 0)
    if days > 0:
        lic["expires"] = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    else:
        lic["expires"] = "Lifetime"

    save_json_with_client_sync(LICENSE_FILE, licenses)
    return True, f"License redeemed successfully! Type: {lic['type']} | Linked to your Discord ID: {discord_id}"

async def send_webhook(license_key, discord_id):
    try:
        # Obtener información de la licencia
        valid, status_msg, license_info = check_license(license_key)
        
        if valid and license_info:
            # Crear el embed usando la función reutilizable
            embed = await create_license_embed(license_key, license_info, bot)
            
            # Personalizar el embed para el webhook
            embed.title = "🎉 New License Redeemed!"
            embed.color = 0xffa500  # Naranja para el webhook
            
            # Agregar información adicional para el webhook
            embed.add_field(
                name="🔑 License Key Used", 
                value=f"`{license_key}`", 
                inline=False
            )
            embed.add_field(
                name="🔗 Webhook Notification", 
                value="A new license has been successfully activated!", 
                inline=False
            )
            
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
                await webhook.send(embed=embed)
        else:
            # Fallback si no se puede obtener la información completa
            embed = discord.Embed(
                title="License Redeemed", 
                color=0xFFA500, 
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="License Key", value=license_key, inline=False)
            embed.add_field(name="Discord ID", value=discord_id, inline=False)
            embed.set_footer(text=f"Linked to Discord ID: {discord_id}")
            
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
                await webhook.send(embed=embed)
            
    except aiohttp.ClientError as e:
        print(f"❌ Webhook error: {e}")
    except Exception as e:
        print(f"❌ Error sending webhook: {e}")

# --- Hold / Activate All Licenses ---
def hold_all_licenses():
    licenses = load_json(LICENSE_FILE)
    for lic in licenses.values():
        lic["active"] = False
    save_json_with_client_sync(LICENSE_FILE, licenses)
    return True, "All licenses are now on hold."

def activate_all_licenses():
    licenses = load_json(LICENSE_FILE)
    for lic in licenses.values():
        lic["active"] = True
    save_json_with_client_sync(LICENSE_FILE, licenses)
    return True, "All licenses have been re-activated."


# --- Verification Function for Tools ---
def verify_license(key, discord_id):
    licenses = load_json(LICENSE_FILE)
    if key not in licenses:
        return False, "License not found"
    
    lic = licenses[key]
    if not lic.get("active", True):
        return False, "License revoked"
    
    # Check if license has expired
    expires = lic.get("expires")
    if expires and expires != "Lifetime":
        try:
            expiry_date = datetime.fromisoformat(expires.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expiry_date:
                return False, "License has expired"
        except (ValueError, TypeError):
            pass  # Invalid date format, continue without expiry check
    
    # Check if already redeemed by different user (anti-sharing)
    if lic.get("redeemed", False) and lic.get("discord_id") != discord_id:
        return False, "License already redeemed by another user"
    
    # If not redeemed yet, redeem it
    if not lic.get("redeemed", False):
        success, msg = redeem_license(key, discord_id)
        return success, msg
    
    # If already redeemed by same user, return success
    return True, f"License verified successfully. Type: {lic.get('type', 'N/A')}"

# --- Bot Setup ---
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

@bot.check
async def globally_block(ctx):
    return ctx.author.id in AUTHORIZED_USERS

# --- Redeem Modal & Button ---
class RedeemModal(Modal):
    def __init__(self):
        super().__init__(title="Redeem Your Key", timeout=300)  # 5 minutos de timeout
        self.key_input = TextInput(label="License Key", placeholder="Enter your license key")
        self.add_item(self.key_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Verificar si la interacción aún es válida
            if not interaction.response.is_done():
                discord_id = interaction.user.id
                key = self.key_input.value
                success, msg = redeem_license(key, discord_id)
                
                if success:
                    # Enviar webhook en segundo plano sin esperar
                    try:
                        await send_webhook(key, discord_id)
                    except Exception as webhook_error:
                        print(f"⚠️ Webhook error (non-critical): {webhook_error}")
                    
                    # Obtener información actualizada de la licencia para mostrar el embed
                    valid, status_msg, license_info = check_license(key)
                    if valid and license_info:
                        # Crear embed con la información de la licencia recién redimida
                        embed = await create_license_embed(key, license_info, interaction.client)
                        embed.title = "🎉 License Successfully Redeemed!"
                        embed.color = 0x00ff00  # Verde para éxito
                        
                        # Agregar mensaje de éxito al embed
                        embed.description = "Your license has been successfully activated!"
                        
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                    else:
                        # Fallback si hay algún problema obteniendo la info
                        success_embed = discord.Embed(
                            title="✅ License Redeemed Successfully!",
                            description=msg,
                            color=0x00ff00,
                            timestamp=datetime.now(timezone.utc)
                        )
                        await interaction.response.send_message(embed=success_embed, ephemeral=True)
                else:
                    # Error en el redeem
                    error_embed = discord.Embed(
                        title="❌ Redeem Failed",
                        description=msg,
                        color=0xff0000,
                        timestamp=datetime.now(timezone.utc)
                    )
                    await interaction.response.send_message(embed=error_embed, ephemeral=True)
            else:
                print("❌ Modal interaction already responded to")
        except discord.errors.NotFound as e:
            print(f"❌ Modal interaction not found: {e}")
        except Exception as e:
            print(f"❌ Error in modal submit: {e}")
            try:
                if not interaction.response.is_done():
                    error_embed = discord.Embed(
                        title="❌ Error",
                        description="Error processing your key. Please try again.",
                        color=0xff0000,
                        timestamp=datetime.now(timezone.utc)
                    )
                    await interaction.response.send_message(embed=error_embed, ephemeral=True)
            except:
                pass
    
    async def on_timeout(self):
        """Maneja el timeout del modal"""
        print("⏰ RedeemModal timed out")

class RedeemView(View):
    def __init__(self):
        super().__init__(timeout=300)  # 5 minutos de timeout

    @discord.ui.button(label="🍊 Redeem Key", style=discord.ButtonStyle.primary)
    async def redeem_button(self, interaction: discord.Interaction, button: Button):
        try:
            # Verificar si la interacción aún es válida
            if not interaction.response.is_done():
                modal = RedeemModal()
                await interaction.response.send_modal(modal)
            else:
                print("❌ Interaction already responded to")
        except discord.errors.NotFound as e:
            print(f"❌ Interaction not found in redeem button: {e}")
        except Exception as e:
            print(f"❌ Error in redeem button: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Error opening redeem form. Please try again.", ephemeral=True)
            except:
                pass
    
    async def on_timeout(self):
        """Maneja el timeout de la vista"""
        print("⏰ RedeemView timed out")
        # Deshabilitar todos los botones
        for item in self.children:
            item.disabled = True

# --- Slash Commands ---
@tree.command(name="gen_key", description="Generate new license(s)", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(duration="Duration of the license", amount="Number of licenses to generate")
@app_commands.choices(duration=[
    app_commands.Choice(name="1 Day", value="1DAY"),
    app_commands.Choice(name="3 Days", value="3DAYS"),
    app_commands.Choice(name="7 Days", value="7DAYS"),
    app_commands.Choice(name="1 Week", value="1WEEK"),
    app_commands.Choice(name="1 Month", value="1MONTH"),
    app_commands.Choice(name="Lifetime", value="LIFETIME")
])
async def gen_key(interaction: discord.Interaction, duration: app_commands.Choice[str], amount: int = 1):
    try:
        if amount < 1:
            amount = 1
        if amount > 50:
            amount = 50
        
        # Responder inmediatamente para evitar timeout
        await interaction.response.defer(ephemeral=True)
        
        # Generar las licencias
        keys = [create_license(duration.value) for _ in range(amount)]
        keys_str = "\n".join(f"`{k}`" for k in keys)
        
        # Enviar resultado
        await interaction.followup.send(f"✅ Generated {len(keys)} license(s):\n{keys_str}", ephemeral=True)
            
    except discord.errors.NotFound:
        # Interacción expirada - no hacer nada, es normal
        pass
    except discord.errors.HTTPException as e:
        # Solo loggear errores HTTP reales (no 404)
        if e.code != 10062:  # 10062 = Unknown interaction
            print(f"❌ HTTP Exception in gen_key: {e}")
        try:
            await interaction.followup.send("❌ Error generating keys. Please try again.", ephemeral=True)
        except:
            pass
    except Exception as e:
        print(f"❌ Error in gen_key: {e}")
        try:
            await interaction.followup.send("❌ An unexpected error occurred. Please try again.", ephemeral=True)
        except:
            pass

@tree.command(name="check_key", description="Check if a license is available or redeemed", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(key="License to check")
async def check_key_cmd(interaction: discord.Interaction, key: str):
    try:
        # Responder inmediatamente para evitar timeout
        await interaction.response.defer(ephemeral=True)
        
        # Verificar la licencia
        valid, msg, license_info = check_license(key)
        
        if not valid:
            # Si la licencia no es válida, enviar mensaje simple
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)
        else:
            # Usar la función reutilizable para crear el embed
            embed = await create_license_embed(key, license_info, interaction.client)
            await interaction.followup.send(embed=embed, ephemeral=True)
            
    except discord.errors.NotFound:
        # Interacción expirada - no hacer nada, es normal
        pass
    except discord.errors.HTTPException as e:
        # Solo loggear errores HTTP reales (no 404)
        if e.code != 10062:  # 10062 = Unknown interaction
            print(f"❌ HTTP Exception in check_key: {e}")
        try:
            await interaction.followup.send("❌ Error checking key. Please try again.", ephemeral=True)
        except:
            pass
    except Exception as e:
        print(f"❌ Error in check_key: {e}")
        try:
            await interaction.followup.send("❌ An unexpected error occurred. Please try again.", ephemeral=True)
        except:
            pass

@tree.command(name="send_redeem_embed", description="Send redeem embed with button", guild=discord.Object(id=GUILD_ID))
async def send_redeem_embed(interaction: discord.Interaction):
    try:
        # Responder inmediatamente para evitar timeout
        await interaction.response.defer(ephemeral=False)
        
        embed = discord.Embed(
            title="Redeem Your Generator Key",
            description=(
                "Instructions:\n"
                "• Click the button below to open the redeem form.\n"
                "• Enter your valid license key.\n"
                "• Once submitted, your license will be activated.\n\n"
                "If you need help, contact our support team."
            ),
            color=0xFFA500,
            timestamp=datetime.now(timezone.utc)
        )
        view = RedeemView()
        
        # Enviar el embed con el botón
        await interaction.followup.send(embed=embed, view=view, ephemeral=False)
            
    except discord.errors.NotFound:
        # Interacción expirada - no hacer nada, es normal
        pass
    except discord.errors.HTTPException as e:
        # Solo loggear errores HTTP reales (no 404)
        if e.code != 10062:  # 10062 = Unknown interaction
            print(f"❌ HTTP Exception in send_redeem_embed: {e}")
        try:
            await interaction.followup.send("❌ Error sending redeem embed. Please try again.", ephemeral=True)
        except:
            pass
    except Exception as e:
        print(f"❌ Error in send_redeem_embed: {e}")
        try:
            await interaction.followup.send("❌ An unexpected error occurred. Please try again.", ephemeral=True)
        except:
            pass

@tree.command(name="delete_all_keys", description="Delete all licenses", guild=discord.Object(id=GUILD_ID))
async def delete_all_keys(interaction: discord.Interaction):
    try:
        # Responder inmediatamente para evitar timeout
        await interaction.response.defer(ephemeral=True)
        
        # Realizar la operación
        save_json_with_client_sync(LICENSE_FILE, {})
        
        # Enviar confirmación
        await interaction.followup.send("✅ All licenses have been deleted.", ephemeral=True)
        
    except discord.errors.NotFound:
        # Interacción expirada - no hacer nada, es normal
        pass
    except discord.errors.HTTPException as e:
        # Solo loggear errores HTTP reales (no 404)
        if e.code != 10062:  # 10062 = Unknown interaction
            print(f"❌ HTTP Exception in delete_all_keys: {e}")
        try:
            await interaction.followup.send("❌ Error deleting keys. Please try again.", ephemeral=True)
        except:
            pass
    except Exception as e:
        print(f"❌ Error in delete_all_keys: {e}")
        try:
            await interaction.followup.send("❌ An unexpected error occurred. Please try again.", ephemeral=True)
        except:
            pass

@tree.command(name="license_status", description="Show status of all licenses", guild=discord.Object(id=GUILD_ID))
async def license_status(interaction: discord.Interaction):
    try:
        # Responder inmediatamente para evitar timeout
        await interaction.response.defer(ephemeral=True)
        
        licenses = load_json(LICENSE_FILE)
        
        if not licenses:
            await interaction.followup.send("📊 No licenses found in the system.", ephemeral=True)
            return
        
        total = len(licenses)
        redeemed = sum(1 for lic in licenses.values() if lic.get('redeemed', False))
        available = total - redeemed
        
        embed = discord.Embed(
            title="📊 License Status Overview",
            color=0x00ff00,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="📈 Total Licenses", value=f"`{total}`", inline=True)
        embed.add_field(name="✅ Redeemed", value=f"`{redeemed}`", inline=True)
        embed.add_field(name="🔓 Available", value=f"`{available}`", inline=True)
        
        # Mostrar estadísticas por tipo
        types_count = {}
        for lic in licenses.values():
            license_type = lic.get('type', 'Unknown')
            types_count[license_type] = types_count.get(license_type, 0) + 1
        
        if types_count:
            types_str = "\n".join([f"• {t}: `{c}`" for t, c in types_count.items()])
            embed.add_field(name="📋 By Type", value=types_str, inline=False)
        
        embed.set_footer(text="License Management System")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except discord.errors.NotFound:
        # Interacción expirada - no hacer nada, es normal
        pass
    except discord.errors.HTTPException as e:
        # Solo loggear errores HTTP reales (no 404)
        if e.code != 10062:  # 10062 = Unknown interaction
            print(f"❌ HTTP Exception in license_status: {e}")
        try:
            await interaction.followup.send("❌ Error getting license status. Please try again.", ephemeral=True)
        except:
            pass
    except Exception as e:
        print(f"❌ Error in license_status: {e}")
        try:
            await interaction.followup.send("❌ An unexpected error occurred. Please try again.", ephemeral=True)
        except:
            pass

@tree.command(name="online_keys", description="Show all online licenses with Discord ID and expiry", guild=discord.Object(id=GUILD_ID))
async def online_keys(interaction: discord.Interaction):
    try:
        # Responder inmediatamente para evitar timeout
        await interaction.response.defer(ephemeral=True)
        
        licenses = load_json(LICENSE_FILE)
        
        if not licenses:
            await interaction.followup.send("📊 No licenses found in the system.", ephemeral=True)
            return
        
        # Filtrar solo licencias redimidas (online)
        online_licenses = {k: v for k, v in licenses.items() if v.get('redeemed', False)}
        
        if not online_licenses:
            await interaction.followup.send("📊 No online licenses found.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🌐 Online Licenses",
            description=f"Total online licenses: `{len(online_licenses)}`",
            color=0x00ff00,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Mostrar hasta 10 licencias para evitar límites de Discord
        count = 0
        for key, info in list(online_licenses.items())[:10]:
            count += 1
            discord_id = info.get('discord_id', 'Unknown')
            expiry = info.get('expiry', 'Unknown')
            license_type = info.get('type', 'Unknown')
            
            # Formatear fecha de expiración
            if expiry != 'Unknown' and expiry != 'Lifetime':
                try:
                    exp_date = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                    expiry = exp_date.strftime('%Y-%m-%d %H:%M UTC')
                except:
                    pass
            
            embed.add_field(
                name=f"🔑 License #{count}",
                value=f"**Key:** `{key[:8]}...`\n**Discord ID:** `{discord_id}`\n**Type:** `{license_type}`\n**Expires:** `{expiry}`",
                inline=True
            )
        
        if len(online_licenses) > 10:
            embed.set_footer(text=f"Showing first 10 of {len(online_licenses)} online licenses")
        else:
            embed.set_footer(text="License Management System")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except discord.errors.NotFound:
        # Interacción expirada - no hacer nada, es normal
        pass
    except discord.errors.HTTPException as e:
        # Solo loggear errores HTTP reales (no 404)
        if e.code != 10062:  # 10062 = Unknown interaction
            print(f"❌ HTTP Exception in online_keys: {e}")
        try:
            await interaction.followup.send("❌ Error getting online keys. Please try again.", ephemeral=True)
        except:
            pass
    except Exception as e:
        print(f"❌ Error in online_keys: {e}")
        try:
            await interaction.followup.send("❌ An unexpected error occurred. Please try again.", ephemeral=True)
        except:
            pass

@tree.command(name="keys_on_hold", description="Put all licenses on hold for maintenance/update", guild=discord.Object(id=GUILD_ID))
async def keys_on_hold_cmd(interaction: discord.Interaction):
    try:
        # Responder inmediatamente para evitar timeout
        await interaction.response.defer(ephemeral=True)
        
        success, msg = keys_on_hold()
        
        if success:
            await interaction.followup.send(f"✅ {msg}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)
            
    except discord.errors.NotFound:
        # Interacción expirada - no hacer nada, es normal
        pass
    except discord.errors.HTTPException as e:
        # Solo loggear errores HTTP reales (no 404)
        if e.code != 10062:  # 10062 = Unknown interaction
            print(f"❌ HTTP Exception in keys_on_hold: {e}")
        try:
            await interaction.followup.send("❌ Error putting keys on hold. Please try again.", ephemeral=True)
        except:
            pass
    except Exception as e:
        print(f"❌ Error in keys_on_hold command: {e}")
        try:
            await interaction.followup.send("❌ An unexpected error occurred. Please try again.", ephemeral=True)
        except:
            pass

@tree.command(name="activate_all_licenses", description="Reactivate all licenses", guild=discord.Object(id=GUILD_ID))
async def activate_all_licenses_cmd(interaction: discord.Interaction):
    try:
        # Responder inmediatamente para evitar timeout
        await interaction.response.defer(ephemeral=True)
        
        success, msg = activate_all_licenses()
        
        if success:
            await interaction.followup.send(f"✅ {msg}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)
            
    except discord.errors.NotFound:
        # Interacción expirada - no hacer nada, es normal
        pass
    except discord.errors.HTTPException as e:
        # Solo loggear errores HTTP reales (no 404)
        if e.code != 10062:  # 10062 = Unknown interaction
            print(f"❌ HTTP Exception in activate_all_licenses: {e}")
        try:
            await interaction.followup.send("❌ Error activating licenses. Please try again.", ephemeral=True)
        except:
            pass
    except Exception as e:
        print(f"❌ Error in activate_all_licenses command: {e}")
        try:
            await interaction.followup.send("❌ An unexpected error occurred. Please try again.", ephemeral=True)
        except:
            pass

@tree.command(name="reset_hwid", description="Reset HWID for a specific license", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(license_key="License key to reset HWID for")
async def reset_hwid(interaction: discord.Interaction, license_key: str):
    try:
        # Responder inmediatamente para evitar timeout
        await interaction.response.defer(ephemeral=True)
        
        licenses = load_json(LICENSE_FILE)
        
        if license_key not in licenses:
            await interaction.followup.send("❌ License key not found.", ephemeral=True)
            return
        
        license_info = licenses[license_key]
        
        if not license_info.get('redeemed', False):
            await interaction.followup.send("❌ This license has not been redeemed yet.", ephemeral=True)
            return
        
        # Reset HWID
        if 'hwid' in license_info:
            old_hwid = license_info['hwid']
            license_info['hwid'] = None
            
            # Guardar cambios
            save_json_with_client_sync(LICENSE_FILE, licenses)
            
            embed = discord.Embed(
                title="✅ HWID Reset Successful",
                description=f"HWID has been reset for license `{license_key[:8]}...`",
                color=0x00ff00,
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(name="🔑 License Key", value=f"`{license_key[:8]}...`", inline=True)
            embed.add_field(name="🖥️ Previous HWID", value=f"`{old_hwid[:16]}...`" if old_hwid else "`None`", inline=True)
            embed.add_field(name="🆕 New HWID", value="`None (Ready for new binding)`", inline=True)
            
            embed.set_footer(text="The license can now be used on a different machine")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send("❌ This license doesn't have an HWID to reset.", ephemeral=True)
            
    except discord.errors.NotFound:
        # Interacción expirada - no hacer nada, es normal
        pass
    except discord.errors.HTTPException as e:
        # Solo loggear errores HTTP reales (no 404)
        if e.code != 10062:  # 10062 = Unknown interaction
            print(f"❌ HTTP Exception in reset_hwid: {e}")
        try:
            await interaction.followup.send("❌ Error resetting HWID. Please try again.", ephemeral=True)
        except:
            pass
    except Exception as e:
        print(f"❌ Error in reset_hwid: {e}")
        try:
            await interaction.followup.send("❌ An unexpected error occurred. Please try again.", ephemeral=True)
        except:
            pass

# --- on_ready ---
@bot.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"✅ Bot is ready! Logged in as {bot.user}")
    
    # Verificar conexión con la API al iniciar
    print("🔍 Verificando conexión con la API...")
    try:
        if test_api_connection():
            print("✅ Conexión con la API establecida correctamente")
        else:
            print("⚠️ No se pudo conectar con la API - El bot funcionará en modo local")
    except Exception as e:
        print(f"⚠️ Error al verificar la API: {e}")

# Iniciar keep-alive para hosting en la nube
keep_alive()

bot.run(BOT_TOKEN)
