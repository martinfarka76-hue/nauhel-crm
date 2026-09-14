import logging

from app.server import build_server
from app.settings import settings

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    app = build_server()
    logging.info("NAUHEL CRM MCP server running on 0.0.0.0:%s (public URL: %s)", settings.port, settings.public_url)
    app.run(transport="streamable-http", host="0.0.0.0", port=settings.port)
