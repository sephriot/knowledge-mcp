"""Entry point for knowledge-mcp server."""

import argparse

from .server import create_server


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
    args = parser.parse_args()

    mcp = create_server(args.data_path or None)
    mcp.run()


if __name__ == "__main__":
    main()
