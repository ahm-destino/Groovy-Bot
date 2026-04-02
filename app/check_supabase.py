import asyncpg
import asyncio

async def check_db():
    try:
        conn = await asyncpg.connect(
            'postgresql://postgres.hwwzbsppzwcyvambeade:GKQEla5wds9ydyRQ@aws-1-eu-west-1.pooler.supabase.com:5432/postgres',
            timeout=10
        )
        
        tables = await conn.fetch('''
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename
        ''')
        
        print('=' * 80)
        print('SUPABASE DATABASE STRUCTURE')
        print('=' * 80)
        
        if not tables:
            print('No tables found - database is empty')
        else:
            print(f'\nFound {len(tables)} tables:\n')
            for table in tables:
                print(f'  - {table[0]}')
            
            print('\n' + '=' * 80)
            print('TABLE DETAILS')
            print('=' * 80)
            
            for table in tables:
                table_name = table[0]
                cols = await conn.fetch(f'''
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position
                ''')
                count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table_name}"')
                
                print(f'\n{table_name.upper()}')
                print(f'  Rows: {count}')
                print(f'  Columns:')
                for col in cols:
                    print(f'    - {col[0]}: {col[1]}')
        
        await conn.close()
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

asyncio.run(check_db())
