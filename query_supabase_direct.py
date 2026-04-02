#!/usr/bin/env python3
"""Check Supabase database structure"""
import asyncpg
import asyncio

SUPABASE_URL = 'postgresql://postgres.hwwzbsppzwcyvambeade:GKQEla5wds9ydyRQ@aws-1-eu-west-1.pooler.supabase.com:5432/postgres'

async def main():
    try:
        print("\n🔌 Connecting to Supabase...")
        conn = await asyncpg.connect(SUPABASE_URL, timeout=10)
        print("✅ Connected!\n")
        
        # Get tables
        tables = await conn.fetch('''
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename
        ''')
        
        print("=" * 80)
        print("📊 SUPABASE DATABASE STRUCTURE")
        print("=" * 80)
        
        if not tables:
            print("\n❌ Database is empty - no tables found\n")
        else:
            print(f"\n✅ Found {len(tables)} tables:\n")
            
            for table in tables:
                table_name = table[0]
                print(f"\n  📋 {table_name.upper()}")
                print("  " + "-" * 76)
                
                # Get columns
                cols = await conn.fetch(f'''
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position
                ''')
                
                # Get row count
                count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table_name}"')
                
                print(f"     Rows: {count}")
                print(f"     Columns:")
                for col in cols:
                    print(f"       • {col[0]:<35} {col[1]}")
        
        await conn.close()
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
