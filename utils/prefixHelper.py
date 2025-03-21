from __future__ import annotations

from objects import glob

class PrefixHelper:
    def __init__(self):
        pass
    
    async def get_prefix(self, guild_id: int) -> str:
        result = await glob.db.fetch("select prefix from guilds where guild_id = %s", [guild_id])
        
        # XXX: r\eturn default prefix if no custom prefix is set
        return result['prefix'] if result else '!'
    
    async def set_prefix(self, guild_id: int, prefix: str) -> None:
        await glob.db.execute(
            'insert into guilds (guild_id, prefix) '
            'values (%s, %s) '
            'on duplicate key update prefix = %s', 
            [guild_id, prefix, prefix])
    
    async def delete_prefix(self, guild_id: int) -> None:
        await glob.db.execute("delete from guilds where guild_id = %s", [guild_id])