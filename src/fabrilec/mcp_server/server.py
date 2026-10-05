import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mcp.server.fastmcp import FastMCP

from src.fabrilec.agent.agent import search_documents as _search_documents
from src.fabrilec.agent.agent import query_database as _query_database

mcp = FastMCP("fabrilec-tenders")


@mcp.tool()
def search_documents(query: str) -> str:
    return _search_documents(query)


@mcp.tool()
def query_database(tender_ref: str) -> str:
    return _query_database(tender_ref)


if __name__ == "__main__":
    mcp.run()