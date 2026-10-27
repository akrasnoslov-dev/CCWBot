from dotenv import dotenv_values
from sqlalchemy.engine import make_url
import asyncpg, asyncio
source=make_url(dotenv_values('D:/Projects/CCWBot/.env')['DATABASE_URL'])
if source.host not in ('localhost','127.0.0.1'):
    raise RuntimeError('Refusing nonlocal database')
url=source.set(drivername='postgresql', port=5432, database='postgres')
async def check():
    try:
        c=await asyncpg.connect(url.render_as_string(hide_password=False), timeout=3)
        try:
            print('local-postgresql-5432-auth-ok',await c.fetchval('select version()')[:30])
        finally: await c.close()
    except Exception as exc:
        print('local-postgresql-5432-auth-unavailable', type(exc).__name__)
asyncio.run(check())
