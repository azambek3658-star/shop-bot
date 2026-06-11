import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: List[int] = field(default_factory=lambda: [
        int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
    ])
    DB_PATH: str = os.getenv("DB_PATH", "shop.db")
    STARS_ENABLED: bool = True
    CRYPTOBOT_TOKEN: str = os.getenv("CRYPTOBOT_TOKEN", "")
    CRYPTOBOT_ENABLED: bool = bool(os.getenv("CRYPTOBOT_TOKEN", ""))
    YOOKASSA_SHOP_ID: str = os.getenv("YOOKASSA_SHOP_ID", "")
    YOOKASSA_SECRET: str = os.getenv("YOOKASSA_SECRET", "")
    YOOKASSA_ENABLED: bool = bool(os.getenv("YOOKASSA_SHOP_ID", ""))
    STEAM_TRADE_URL: str = os.getenv("STEAM_TRADE_URL", "")
    STEAM_ENABLED: bool = bool(os.getenv("STEAM_TRADE_URL", ""))
    LOLZ_TOKEN: str = os.getenv("LOLZ_TOKEN", "")
    LOLZ_ENABLED: bool = bool(os.getenv("LOLZ_TOKEN", ""))
    SHOP_NAME: str = os.getenv("SHOP_NAME", "🛒 Магазин")
    SUPPORT_USERNAME: str = os.getenv("SUPPORT_USERNAME", "")
    MIN_BALANCE_ALERT: float = float(os.getenv("MIN_BALANCE_ALERT", "5"))

config = Config()
