import os, urllib.request, json
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

AUTHORIZED_EMAIL = os.getenv("AUTHORIZED_USER_EMAIL", "")

def verify_google_oauth_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Validates Google OAuth Bearer Token against Google TokenInfo Endpoint.
    """
    if not credentials or not credentials.credentials:
        # If OAuth is not configured or in local dev, allow bypass if explicitly disabled
        if os.getenv("DISABLE_AUTH", "false").lower() == "true":
            return {"email": "dev_user@local"}
        raise HTTPException(status_code=401, detail="Falta cabecera de autenticación Authorization: Bearer <token>")

    token = credentials.credentials
    try:
        url = f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            user_email = data.get("email", "")
            
            if AUTHORIZED_EMAIL and user_email.lower() != AUTHORIZED_EMAIL.lower():
                raise HTTPException(status_code=403, detail=f"Usuario no autorizado: {user_email}")
                
            return data
    except Exception as e:
        # If id_token check failed, try access_token check
        try:
            url_access = f"https://www.googleapis.com/oauth2/v3/userinfo"
            req_acc = urllib.request.Request(url_access, headers={'Authorization': f'Bearer {token}'})
            with urllib.request.urlopen(req_acc) as resp2:
                data2 = json.loads(resp2.read().decode('utf-8'))
                user_email2 = data2.get("email", "")
                if AUTHORIZED_EMAIL and user_email2.lower() != AUTHORIZED_EMAIL.lower():
                    raise HTTPException(status_code=403, detail=f"Usuario no autorizado: {user_email2}")
                return data2
        except Exception:
            raise HTTPException(status_code=401, detail="Token OAuth 2.0 inválido o caducado")
