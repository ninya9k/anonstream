import asyncio

from anonstream.control.exceptions import ControlSocketExit, CommandFailed
from anonstream.control.parse import parse

def start_control_server_at(address):
    return asyncio.start_unix_server(serve_control_client, address)

async def serve_control_client(reader, writer):
    while line := await reader.readline():
        try:
            request = line.decode('utf-8')
        except UnicodeDecodeError as e:
            normal, response = None, str(e)
        else:
            try:
                normal, response = await parse(request)
            except CommandFailed as e:
                normal, response = None, e.args[0] + '\n'
            except ControlSocketExit:
                writer.close()
                break

        if normal is not None:
            for index, word in enumerate(normal):
                if index > 0:
                    writer.write(b' ')
                writer.write(word.encode())
            writer.write(b'\n')
        elif response:
            writer.write(b'error: ')

        writer.write(response.encode())
        await writer.drain()
