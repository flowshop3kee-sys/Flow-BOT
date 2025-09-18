# 🚀 Guía de Despliegue - Discord Bot 24/7

## ✅ Tu bot ya está preparado para hosting gratuito!

He configurado tu bot para que funcione 24/7 en servicios de hosting gratuitos. Aquí tienes las opciones:

---

## 🌟 **OPCIÓN 1: Railway (RECOMENDADO)**

### ¿Por qué Railway?
- ✅ $5 USD gratis cada mes
- ✅ No se duerme como otros servicios
- ✅ Muy fácil de configurar
- ✅ Perfecto para bots Discord

### Pasos para Railway:

1. **Crear cuenta en Railway**
   - Ve a [railway.app](https://railway.app)
   - Regístrate con GitHub

2. **Subir tu código a GitHub**
   - Crea un repositorio en GitHub
   - Sube todos los archivos de tu bot
   - **IMPORTANTE**: No subas el archivo `.env` (ya está en .gitignore)

3. **Desplegar en Railway**
   - En Railway, haz clic en "New Project"
   - Selecciona "Deploy from GitHub repo"
   - Elige tu repositorio del bot
   - Railway detectará automáticamente que es un proyecto Python

4. **Configurar variables de entorno**
   - En Railway, ve a tu proyecto → Variables
   - Agrega estas variables:
     ```
     BOT_TOKEN=tu_token_aqui
     GUILD_ID=1416508318876176462
     WEBHOOK_URL=tu_webhook_url
     AUTHORIZED_USERS=1417259225100582973
     ```

5. **¡Listo!** Tu bot estará online 24/7

---

## 🔄 **OPCIÓN 2: Render**

### Pasos para Render:

1. **Crear cuenta en Render**
   - Ve a [render.com](https://render.com)
   - Regístrate con GitHub

2. **Crear Web Service**
   - New → Web Service
   - Conecta tu repositorio de GitHub
   - Configuración:
     - **Environment**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `python main.py`

3. **Variables de entorno**
   - En Environment, agrega las mismas variables que en Railway

4. **Nota**: Render se duerme después de 15 minutos sin actividad, pero se reactiva automáticamente

---

## 🆓 **OPCIÓN 3: Replit (Para principiantes)**

### Pasos para Replit:

1. **Crear cuenta en Replit**
   - Ve a [replit.com](https://replit.com)
   - Crea una cuenta

2. **Crear nuevo Repl**
   - New Repl → Import from GitHub
   - Pega la URL de tu repositorio

3. **Configurar Secrets**
   - En el panel izquierdo, ve a "Secrets"
   - Agrega las variables de entorno

4. **Mantener activo con UptimeRobot**
   - Ve a [uptimerobot.com](https://uptimerobot.com)
   - Crea un monitor HTTP que haga ping a tu Repl cada 5 minutos
   - URL del monitor: `https://tu-repl-name.tu-username.repl.co`

---

## 📋 **Archivos que he creado para ti:**

- ✅ **`.env`** - Variables de entorno (NO subir a GitHub)
- ✅ **`config.py`** - Configuración segura
- ✅ **`keep_alive.py`** - Servidor web para mantener el bot activo
- ✅ **`Procfile`** - Configuración para Railway/Heroku
- ✅ **`runtime.txt`** - Versión de Python
- ✅ **`.gitignore`** - Protege archivos sensibles
- ✅ **`requirements.txt`** - Dependencias actualizadas

---

## 🔧 **Cambios realizados en tu código:**

1. **Seguridad mejorada**: Tokens movidos a variables de entorno
2. **Keep-alive agregado**: Mantiene el bot activo en servicios cloud
3. **Configuración modular**: Código más organizado y seguro

---

## 🚨 **IMPORTANTE - Antes de desplegar:**

1. **Nunca subas el archivo `.env` a GitHub**
2. **Configura las variables de entorno en el servicio de hosting**
3. **Tu bot funcionará exactamente igual que ahora, pero 24/7**

---

## 💡 **Mi recomendación:**

**Para tu bot de licencias, usa Railway** porque:
- No se duerme nunca
- $5 gratis al mes es suficiente para tu bot
- Configuración súper fácil
- Mejor rendimiento

---

## 🆘 **¿Necesitas ayuda?**

Si tienes problemas:
1. Verifica que todas las variables de entorno estén configuradas
2. Revisa los logs del servicio de hosting
3. Asegúrate de que el archivo `requirements.txt` esté actualizado

**¡Tu bot ya está listo para funcionar 24/7! 🎉**