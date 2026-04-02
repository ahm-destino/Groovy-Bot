#!/usr/bin/env python3
"""Check Supabase database structure and data"""
import asyncpg
import asyncio
import json
from datetime import datetime


async def check_db():
    try:
        conn = await asyncpg.connect(
            'postgresql://postgres.hwwzbsppzwcyvambeade:GKQEla5wds9ydyRQ@aws-1-eu-west-1.pooler.supabase.com:5432/postgres',
            timeout=10
        )
        
        # Get all tables in public schema
        tables = await conn.fetch('''
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename
        ''')
        
        print('=' * 80)
        print('📊 SUPABASE DATABASE STRUCTURE')
        print('=' * 80)
        
        if not tables:
            print('❌ No tables found in public schema (DB is empty)')
            await conn.close()
            return
        
        print(f'\n✅ Found {len(tables)} tables:\n')
        for table in tables:
            print(f'  ✓ {table[0]}')
        
        print('\n' + '=' * 80)
        print('📋 DETAILED TABLE STRUCTURE & DATA')
        print('=' * 80)
        
        for table in tables:
            table_name = table[0]
            
            # Get columns
            cols = await conn.fetch(f'''
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            ''')
            
            # Get row count
            count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table_name}"')
            
            print(f'\n▶️  {table_name.upper()}')
            print(f'   📍 Rows: {count}')
            print(f'   📋 Columns:')
            for col in cols:
                print(f'      • {col[0]:<30} | {col[1]}')
            
            # Show sample data if table has rows
            if count > 0 and count <= 5:
                print(f'   📄 Sample Data:')
                rows = await conn.fetch(f'SELECT * FROM "{table_name}" LIMIT 3')
                for i, row in enumerate(rows, 1):
                    print(f'      Row {i}: {dict(row)}')
            elif count > 5:
                print(f'   📄 Sample Data (first 2 rows):')
                rows = await conn.fetch(f'SELECT * FROM "{table_name}" LIMIT 2')
                for i, row in enumerate(rows, 1):
                    print(f'      Row {i}: {dict(row)}')
        
        await conn.close()
        print('\n' + '=' * 80)
        print('✅ Database check complete!')
        print('=' * 80)
        
    except Exception as e:
        print(f'❌ Error connecting to Supabase: {e}')
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(check_db())
