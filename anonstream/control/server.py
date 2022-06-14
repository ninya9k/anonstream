import asyncio

from anonstream.control.exceptions import Exit
from anonstream.control.parse import parse_request

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
                normal, response = await parse_request(request)
            except Exit:
                writer.close()
                break

        if normal is not None:
            normal_method, normal_options = normal
            if normal_method is not None:
                writer.write(normal_method.encode())
                for arg in normal_options:
                    writer.write(b' ')
                    writer.write(arg.encode())
                writer.write(b'\n')
        elif response:
            writer.write(b'error: ')

        writer.write(response.encode())
        await writer.drain()
