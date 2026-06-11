import logging
from typing import Optional
from LOLZTEAM.Client import Market

logger = logging.getLogger(__name__)

class LolzBuyer:
    def __init__(self, token):
        self.token = token
        self.market = Market(token=token)

    async def buy(self, item_id: int) -> Optional[str]:
        try:
            response = await self.market.managing.fast_buy(item_id=item_id)
            data = response.json()
            if data.get("status") == "ok" or data.get("item"):
                item = data.get("item", {})
                login = item.get("login", "")
                password = item.get("password", "")
                if login and password:
                    return f"Логин: {login}\nПароль: {password}"
                return str(item)
            logger.error("Lolz buy error: %s", data)
        except Exception as e:
            logger.error("Lolz exception: %s", e)
        return None
