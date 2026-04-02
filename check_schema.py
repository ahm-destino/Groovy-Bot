import asyncio
import asyncpg

async def main():
    try:
        conn = await asyncpg.connect(
            'postgresql://postgres.hwwzbsppzwcyvambeade:GKQEla5wds9ydyRQ@aws-1-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require'
        )
        data = await conn.fetch("SELECT table_schema, table_name, column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'phone'")
        for d in data:
            print(dict(d))
        await conn.close()
    except Exception as e:
        print(e)

asyncio.run(main())
