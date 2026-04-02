import asyncio
import asyncpg

async def main():
    try:
        conn = await asyncpg.connect('postgresql://postgres.hwwzbsppzwcyvambeade:GKQEla5wds9ydyRQ@aws-1-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require')
        
        events = await conn.fetchval('SELECT COUNT(*) FROM events')
        bookings = await conn.fetchval('SELECT COUNT(*) FROM bookings')
        tickets = await conn.fetchval('SELECT COUNT(*) FROM tickets')
        
        print(f'Events: {events}')
        print(f'Bookings: {bookings}')
        print(f'Tickets: {tickets}')
        
        if events > 0:
            print("\nSaved Events Details:")
            records = await conn.fetch('SELECT title, venue_name, location_lat, location_lng FROM events LIMIT 5')
            for r in records:
                print(dict(r))
                
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
