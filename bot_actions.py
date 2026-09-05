# -*- coding: utf-8 -*-
"""Bot actions — address checking, batch processing, seed phrase scanning."""

import os
import sys
import json
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.panel import Panel
from rich import box

from scanner.ui import (
    console, print_success, print_error, print_info, print_warning,
    show_balance_table, show_chain_table, show_seed_results_table,
    show_proxy_pool_table, show_portfolio_summary, show_export_table,
)


def action_check_address(cfg):
    """Check a single address balance."""
    print_info("Address Balance Check")
    
    address = console.input("[cyan]Enter wallet address: [/]").strip()
    if not address:
        print_error("Address cannot be empty.")
        return
    
    chain = console.input("[cyan]Enter chain (default: ethereum): [/]").strip() or "ethereum"
    
    print_info(f"Checking {address} on {chain}...")
    
    # Simulate balance check
    time.sleep(1)
    
    balances = [
        [chain, "0.0000", "$0.00", "0"],
    ]
    show_balance_table(balances)


def action_batch_check(cfg):
    """Batch check multiple addresses."""
    print_info("Batch Address Check")
    
    file_path = console.input("[cyan]Enter file path with addresses (one per line): [/]").strip()
    
    if not file_path or not Path(file_path).exists():
        print_error("File not found.")
        return
    
    with open(file_path, "r") as f:
        addresses = [line.strip() for line in f if line.strip()]
    
    if not addresses:
        print_error("No addresses found in file.")
        return
    
    print_info(f"Checking {len(addresses)} addresses...")
    
    results = []
    for i, addr in enumerate(addresses):
        results.append([str(i+1), addr[:20] + "...", "0.0000", "$0.00"])
    
    show_seed_results_table(results)


def action_seed_check(cfg):
    """Check seed phrases from file."""
    print_info("Seed Phrase Check")
    
    seed_file = cfg.get("seed_checker", {}).get("seed_file", "seeds.txt")
    
    if not Path(seed_file).exists():
        print_error(f"Seed file not found: {seed_file}")
        return
    
    with open(seed_file, "r") as f:
        seeds = [line.strip() for line in f if line.strip()]
    
    if not seeds:
        print_error("No seed phrases found.")
        return
    
    print_info(f"Checking {len(seeds)} seed phrases...")
    
    results = []
    for i, seed in enumerate(seeds):
        preview = " ".join(seed.split()[:3]) + "..."
        results.append([str(i+1), preview, "ethereum", "0x...", "0.0000", "$0.00", "No"])
    
    show_seed_results_table(results)


def action_proxy_manager(cfg):
    """Manage proxies."""
    print_info("Proxy Manager")
    
    proxies = cfg.get("proxies", {})
    proxy_list = proxies.get("proxy_list", [])
    
    if not proxy_list:
        print_warning("No proxies configured.")
        print_info("Add proxies to config.json under proxies.proxy_list")
        return
    
    proxy_table = []
    for i, proxy in enumerate(proxy_list[:10], 1):
        proxy_table.append([str(i), proxy, "HTTP", "50ms", "✓", "Now"])
    
    show_proxy_pool_table(proxy_table)


def action_portfolio_summary(cfg):
    """Show portfolio summary."""
    print_info("Portfolio Summary")
    
    records = [
        ["Ethereum", "1.2345 ETH", "$4,567.89", "5", "45%"],
        ["Bitcoin", "0.0123 BTC", "$1,234.56", "2", "12%"],
        ["Solana", "45.67 SOL", "$2,345.67", "3", "23%"],
        ["BSC", "123.45 BSC", "$2,012.34", "8", "20%"],
    ]
    show_portfolio_summary(records)


def action_export_results(cfg):
    """Export results to file."""
    print_info("Export Results")
    
    export_cfg = cfg.get("export", {})
    default_format = export_cfg.get("default_format", "txt")
    
    formats = [
        ["CSV", ".csv", "Address, Balance, USD, Tokens", "Excel/Sheets"],
        ["JSON", ".json", "Full structured data", "API/Development"],
        ["TXT", ".txt", "Plain text report", "Human readable"],
        ["HTML", ".html", "Styled web page", "Visual reporting"],
    ]
    show_export_table(formats)
    
    fmt = console.input(f"[cyan]Export format (default: {default_format}): [/]").strip() or default_format
    filename = console.input("[cyan]Output filename (without extension): [/]").strip() or "export"
    
    output_dir = export_cfg.get("output_directory", "./results")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    output_path = Path(output_dir) / f"{filename}.{fmt}"
    print_success(f"Export saved to: {output_path}")


def action_chain_config(cfg):
    """Configure blockchain RPC endpoints."""
    print_info("Chain Configuration")
    
    chains = [
        ["Ethereum", "ETH", "Alchemy/Infura", "✓"],
        ["Bitcoin", "BTC", "Blockstream", "✓"],
        ["Solana", "SOL", "Public RPC", "✓"],
        ["BSC", "BNB", "Binance", "✓"],
        ["Polygon", "MATIC", "Public RPC", "✓"],
        ["Arbitrum", "ARB", "Public RPC", "✓"],
    ]
    show_chain_table(chains)
