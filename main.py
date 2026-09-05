# -*- coding: utf-8 -*-
"""
Crypto Checker — Entry Point
"""
import sys
import os
import json
import threading
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scanner.ui import (
    print_banner,
    print_info,
    print_error,
    print_success,
    show_menu_table,
    console,
)
from config import load_config
from bot_actions import (
    action_check_address,
    action_batch_check,
    action_seed_check,
    action_proxy_manager,
    action_portfolio_summary,
    action_export_results,
    action_chain_config,
)
from actions.install import action_install_dependencies
from actions.settings import action_settings
from actions.about import action_about
from actions.scan import action_prometheus_scan


MENU_ITEMS = [
    ("1", "💰", "Check Address Balance", "Single address lookup via proxy"),
    ("2", "📦", "Batch Address Check", "Multiple addresses, multi-thread"),
    ("3", "🌱", "Seed Phrase Check", "Check seed phrases from file"),
    ("4", "🔄", "Proxy Manager", "Load, validate, rotate proxies"),
    ("5", "📊", "Portfolio Summary", "Aggregated results dashboard"),
    ("6", "📤", "Export Results", "Save to TXT / CSV / JSON"),
    ("7", "⛓️ ", "Chain Configuration", "RPC endpoints & settings"),
    ("8", "⚙️ ", "Settings", "Threads, timeouts, preferences"),
    ("9", "🔐", "Prometheus Scan", "Browser data + crypto wallet extraction"),
    ("0", "🚪", "Exit", "Close application"),
]


def main():
    print_banner()
    cfg = load_config()

    while True:
        choice = show_menu_table(MENU_ITEMS)

        if choice == "0":
            print_info("Goodbye!")
            sys.exit(0)
        elif choice == "1":
            action_check_address(cfg)
        elif choice == "2":
            action_batch_check(cfg)
        elif choice == "3":
            action_seed_check(cfg)
        elif choice == "4":
            action_proxy_manager(cfg)
        elif choice == "5":
            action_portfolio_summary(cfg)
        elif choice == "6":
            action_export_results(cfg)
        elif choice == "7":
            action_chain_config(cfg)
        elif choice == "8":
            action_settings()
        elif choice == "9":
            action_prometheus_scan(cfg)
        else:
            print_error("Invalid option. Enter 0–9.")

        cfg = load_config()
        console.input("\n[dim]Press Enter to return to menu...[/]")


if __name__ == "__main__":
    main()
