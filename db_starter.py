import os
import sqlite3
import asyncio
import aiosqlite

db_path = 'ids.db'

# Remove the old database if it exists
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Database file removed: {db_path}")


# Initialize the database and create tables asynchronously
async def initialize_db():
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            id TEXT PRIMARY KEY
        )
        ''')
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS delivery_ids (
            id TEXT PRIMARY KEY
        )
        ''')
        await conn.commit()
        print("Database initialized and tables created.")


# Set the admin ID in the database asynchronously
async def set_admin_id(admin_id):
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute('DELETE FROM admin')
        await conn.execute('INSERT INTO admin (id) VALUES (?)', (admin_id,))
        await conn.commit()
        print(f"Admin ID set to {admin_id}")


# Ensure the admin ID is set
async def ensure_admin_set():
    async with aiosqlite.connect(db_path) as conn:
        async with conn.execute('SELECT id FROM admin LIMIT 1') as cursor:
            row = await cursor.fetchone()
            if row is None:
                await set_admin_id('6588562022')


# Run the database initialization and admin setup
async def main():
    await initialize_db()
    await ensure_admin_set()


# Run the main function to initialize the database and set the admin ID
asyncio.run(main())
