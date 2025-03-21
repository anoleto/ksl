from __future__ import annotations

from typing import Optional
import httpx
import config

class ApiClient:
    def __init__(self, server: str = config.Bancho):
        """API client for Bancho.py based osu! server."""
        self.server = server
        self.key = config.BanchoApiKey  # api key | actually why
        self.client = httpx.AsyncClient(base_url=f"https://api.{self.server}/v1/", timeout=5.0)

    async def _get(self, endpoint: str, params: dict) -> dict:
        response = await self.client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()

    async def get_player_scores(self, scope: str, user_id: Optional[int] = None,
                                 username: Optional[str] = None, mods_arg: Optional[str] = None,
                                 mode_arg: Optional[int] = None) -> dict:
        params = {
            "name": username,
            "id": user_id,
            "mods": mods_arg,
            "mode": mode_arg,
            "scope": scope # recent | best
        }
        
        return await self._get("get_player_scores", {k: v for k, v in params.items() if v is not None})

    async def get_map_info(self, map_id: Optional[int] = None, md5: Optional[str] = None) -> dict:
        params = {
            "id": map_id,
            "md5": md5
        }

        return await self._get("get_map_info", {k: v for k, v in params.items() if v is not None})

    async def get_player_info(self, scope: str, user_id: Optional[int] = None,
                               username: Optional[str] = None) -> dict:
        params = {
            "id": user_id,
            "name": username,
            "scope": scope, # all | stats | info
        }

        return await self._get("get_player_info", {k: v for k, v in params.items() if v is not None})
    
    async def get_map_scores(self, scope: str, user_id: Optional[int] = None,
                                 username: Optional[str] = None, mods_arg: Optional[str] = None,
                                 mode_arg: Optional[int] = None) -> dict:
        params = {
            "name": username,
            "id": user_id,
            "mods": mods_arg,
            "mode": mode_arg,
            "scope": scope # recent | best
        }
        
        return await self._get("get_map_scores", {k: v for k, v in params.items() if v is not None})
                
    async def close(self):
        await self.client.aclose()