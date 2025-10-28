#!/usr/bin/env python3
"""
Personal Finance App - Main Entry Point

Run with: python finance.py <command> [options]
Or: chmod +x finance.py && ./finance.py <command> [options]
"""

from cli.finance_cli import cli

if __name__ == '__main__':
    cli()
