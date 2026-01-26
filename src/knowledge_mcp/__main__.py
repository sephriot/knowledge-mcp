"""Entry point for knowledge-mcp server."""

import argparse

from knowledge_mcp.server import create_server


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Knowledge MCP Server - Project-specific knowledge management"
    )
    parser.add_argument(
        "--data-path",
        default="",
        help="Path to knowledge storage (default: .knowledge or KNOWLEDGE_MCP_PATH env)",
    )
    parser.add_argument(
        "--persist-popularity",
        action="store_true",
        help="Persist popularity counts to disk on each atom retrieval",
    )
    args = parser.parse_args()

    mcp = create_server(
        data_path=args.data_path or None,
        persist_popularity=args.persist_popularity,
    )
    mcp.run()


if __name__ == "__main__":
    main()
