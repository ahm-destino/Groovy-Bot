#!/usr/bin/env python3
"""Clear all data from Supabase database"""
import asyncpg
import asyncio

SUPABASE_URL = 'postgresql://postgres.hwwzbsppzwcyvambeade:GKQEla5wds9ydyRQ@aws-1-eu-west-1.pooler.supabase.com:5432/postgres'

async def main():
    try:
        print("\n🔌 Connecting to Supabase...")
        conn = await asyncpg.connect(SUPABASE_URL, timeout=10)
        print("✅ Connected!\n")
        
        # Tables to clear
        tables = [
            'bookings',
            'tickets',
            'events',
            'message_logs',
            'interaction_logs',
            'conversations',
            'users'
        ]
        
        print("🗑️  Clearing tables...\n")
        for table in tables:
            try:
                await conn.execute(f'TRUNCATE TABLE "{table}" CASCADE')
                print(f"  ✅ {table}")
            except Exception as e:
                print(f"  ⚠️  {table}: {e}")
        
        print("\n📊 Verifying cleared data...\n")
        for table in tables:
            count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table}"')
            print(f"  {table}: {count} rows")
        
        await conn.close()
        print("\n✅ Database cleared successfully!\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
