from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def test_connection():
    client = AsyncIOMotorClient("mongodb+srv://enukolupriyanka:PriyankaE@empdetails.amw7vfl.mongodb.net/")
    try:
        await client.admin.command('ping')
        print("MongoDB connection successful")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")

asyncio.run(test_connection())