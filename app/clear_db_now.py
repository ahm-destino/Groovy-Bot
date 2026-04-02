#!/usr/bin/env python3
"""Clear Supabase database for fresh testing"""
import asyncpg
import asyncio

async def clear_db():
    try:
        print('Connecting to Supabase...')
        conn = await asyncpg.connect(
            'postgresql://postgres.hwwzbsppzwcyvambeade:GKQEla5wds9ydyRQ@aws-1-eu-west-1.pooler.supabase.com:5432/postgres',
            timeout=10
        )
        print('✅ Connected to Supabase!\n')
        
        tables = ['users', 'conversations', 'message_logs', 'interaction_logs', 'tickets', 'bookings', 'events', 'promo_codes', 'ticket_tiers']
        
        print('🗑️  Clearing tables...\n')
        for table in tables:
            try:
                await conn.execute(f'TRUNCATE TABLE {table} CASCADE;')
                print(f'✅ Cleared {table}')
            except Exception as e:
                print(f'⚠️  {table}: {e}')
        
        await asyncio.sleep(1)
        
        users = await conn.fetchval('SELECT COUNT(*) FROM users')
        convos = await conn.fetchval('SELECT COUNT(*) FROM conversations')
        events = await conn.fetchval('SELECT COUNT(*) FROM events')
        
        print(f'\n📊 Final Database State:')
        print(f'   Users: {users}')
        print(f'   Conversations: {convos}')
        print(f'   Events: {events}')
        
        if users == 0 and convos == 0 and events == 0:
            print('\n✅✅✅ SUPABASE IS CLEAN! READY TO TEST!\n')
        
        await conn.close()
    except Exception as e:
        print(f'ERROR: {e}')
        import traceback
        traceback.print_exc()

asyncio.run(clear_db())
