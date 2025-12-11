import os

class Environment:
    DEVELOPMENT = "development"
    PRODUCTION = "production"

CONFIG = {
    "development": {
        "database_url": "mysql+pymysql://root:Kevin0224@localhost/kaimo_bd",
        "frontend_url": "http://localhost:4200",
        "api_url": "http://localhost:8000",
        "debug": True,
        "docs_enabled": True,
    },
    
    "production": {
        "database_url": "mysql+pymysql://usuario:password@host.railway.app:3306/kaimo_bd",
        "frontend_url": "https://kaimo.up.railway.app",
        "api_url": "https://backendkaimo-production.up.railway.app",
        "debug": False,
        "docs_enabled": False,
    },
    "current": "production" 
}

def get_config():
    current = CONFIG["current"]
    return CONFIG[current]

def get_cors_origins():
    config = get_config()
    if CONFIG["current"] == "production":
        return [config["frontend_url"]]
    else:
        return [
            "http://localhost:4200",
            "http://127.0.0.1:4200",
            config["frontend_url"]
        ]