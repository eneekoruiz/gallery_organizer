import os, urllib.request, json

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

def send_notification(title: str, message: str, level: str = "INFO"):
    """
    Envía notificaciones silenciosas a un Webhook de Telegram o Discord.
    """
    if not WEBHOOK_URL:
        print(f"[{level}] {title}: {message} (Webhook no configurado)")
        return False

    emoji_map = {
        "INFO": "🟢",
        "WARNING": "⚠️",
        "ERROR": "🚨",
        "SUCCESS": "🎉"
    }
    emoji = emoji_map.get(level.upper(), "📢")
    
    payload = {
        "content": f"{emoji} **[{level.upper()}] {title}**\n{message}",
        "text": f"{emoji} *{title}*\n{message}" # Compatible Telegram / Discord
    }

    try:
        data_bytes = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            WEBHOOK_URL,
            data=data_bytes,
            headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req) as resp:
            print(f"✓ Notificación enviada a Webhook con éxito ({title})")
            return True
    except Exception as e:
        print("Error al enviar notificación a Webhook:", e)
        return False
