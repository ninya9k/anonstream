import asyncio

from werkzeug.wrappers import Response as WerkzeugResponse
from quart.app import Quart as Quart_
from quart.asgi import ASGIHTTPConnection as ASGIHTTPConnection_
from quart.utils import encode_headers


RESPONSE_ITERATOR_TIMEOUT = 10


class ASGIHTTPConnection(ASGIHTTPConnection_):
    async def _send_response(self, send, response):
        await send({
            "type": "http.response.start",
            "status": response.status_code,
            "headers": encode_headers(response.headers),
        })

        if isinstance(response, WerkzeugResponse):
            for data in response.response:
                body = data.encode(response.charset) if isinstance(data, str) else data
                await asyncio.wait_for(
                    send({
                        "type": "http.response.body",
                        "body": body,
                        "more_body": True,
                    }),
                    timeout=RESPONSE_ITERATOR_TIMEOUT,
                )
        else:
            async with response.response as response_body:
                async for data in response_body:
                    body = data.encode(response.charset) if isinstance(data, str) else data
                    await asyncio.wait_for(
                        send({
                            "type": "http.response.body",
                            "body": body,
                            "more_body": True,
                        }),
                        timeout=RESPONSE_ITERATOR_TIMEOUT,
                    )
        await send({
            "type": "http.response.body",
            "body": b"",
            "more_body": False,
        })


class Quart(Quart_):
    asgi_http_class = ASGIHTTPConnection
