import asyncio
import anonstream

async def main():
    app = await anonstream.create_app()
    await app.run_task(port=5051, debug=True)

if __name__ == '__main__':
    asyncio.run(main())
