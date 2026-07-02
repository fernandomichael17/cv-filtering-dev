import asyncio
import asyncpg
import os

async def test():
    try:
        conn = await asyncpg.connect(
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            host=os.environ['DB_HOST'].strip(),
            port=os.environ['DB_PORT'],
            database=os.environ['DB_NAME']
        )
        print("Success")
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())
