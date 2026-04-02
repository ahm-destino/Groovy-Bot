import asyncio
import asyncpg

async def main():
    try:
        print("Connecting to Supabase...")
        conn = await asyncpg.connect(
            'postgresql://postgres.hwwzbsppzwcyvambeade:GKQEla5wds9ydyRQ@aws-1-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require'
        )
        print("[OK] Connected to Supabase!")
        
        tables = ['users', 'conversations', 'message_logs', 'interaction_logs', 'tickets', 'bookings', 'events', 'promo_codes', 'ticket_tiers']
        
        for table in tables:
            try:
                await conn.execute(f'TRUNCATE TABLE {table} CASCADE;')
                print(f"[OK] Cleared {table}")
            except Exception as e:
                print(f"[SKIP] {table}: {e}")
        
        users = await conn.fetchval('SELECT COUNT(*) FROM users')
        convos = await conn.fetchval('SELECT COUNT(*) FROM conversations')
        
        print(f"\n--- Final state ---")
        print(f"   Users: {users}")
        print(f"   Conversations: {convos}")
        
        if users == 0 and convos == 0:
            print("\n[DONE] SUPABASE IS CLEAN! READY TO TEST!\n")
        else:
            print(f"\n[WARN] Some rows remain: users={users}, conversations={convos}")
        
        await conn.close()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(main())
