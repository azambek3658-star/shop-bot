import logging
import aiohttp

logger = logging.getLogger(__name__)
CRYPTOBOT_API = "https://pay.crypt.bot/api"

class CryptoBotPayment:
    def __init__(self, token):
        self.token = token
        self.headers = {"Crypto-Pay-API-Token": token}

    async def create_invoice(self, amount, currency, description, payload):
        try:
            async with aiohttp.ClientSession() as session:
                resp = await session.post(
                    f"{CRYPTOBOT_API}/createInvoice",
                    headers=self.headers,
                    json={
                        "asset": currency,
                        "amount": str(amount),
                        "description": description,
                        "payload": payload,
                        "allow_comments": False,
                        "allow_anonymous": False,
                    }
                )
                data = await resp.json()
                if data.get("ok"):
                    inv = data["result"]
                    return {"pay_url": inv["pay_url"], "amount": inv["amount"]}
                logger.error("CryptoBot error: %s", data)
        except Exception as e:
            logger.error("CryptoBot exception: %s", e)
        return None

    async def check_invoice(self, payload):
        try:
            async with aiohttp.ClientSession() as session:
                resp = await session.get(
                    f"{CRYPTOBOT_API}/getInvoices",
                    headers=self.headers,
                    params={"status": "paid"}
                )
                data = await resp.json()
                if data.get("ok"):
                    for inv in data["result"].get("items", []):
                        if inv.get("payload") == payload:
                            return True
        except Exception as e:
            logger.error("CryptoBot check error: %s", e)
        return False
