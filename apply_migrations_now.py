import asyncio
import asyncpg
import os

async def main():
    try:
        print("Connecting to Supabase...")
        conn = await asyncpg.connect(
            'postgresql://postgres.hwwzbsppzwcyvambeade:GKQEla5wds9ydyRQ@aws-1-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require'
        )
        print("[OK] Connected to Supabase!")

        # The migrations directory
        migrations_dir = 'migrations'
        
        # Files to apply in order (add_bot_fields.sql handles core tables)
        files = [
            'add_bot_fields.sql',
            'add_interaction_logs.sql',
            'add_promo_codes.sql',
            'add_ticket_tiers.sql',
            'add_gift_tickets.sql'
        ]

        for filename in files:
            filepath = os.path.join(migrations_dir, filename)
            if os.path.exists(filepath):
                print(f"Applying {filename}...")
                with open(filepath, 'r', encoding='utf-8') as f:
                    sql = f.read()
                try:
                    await conn.execute(sql)
                    print(f"[OK] Applied {filename}")
                except Exception as e:
                    import traceback
                    # Only print the error, don't crash the script to allow other migrations
                    print(f"[FAIL] Failed to apply {filename}: {type(e).__name__} - {str(e)}")
            else:
                print(f"[WARN] File not found: {filepath}")

        await conn.close()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(main())
