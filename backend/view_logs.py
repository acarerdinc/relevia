#!/usr/bin/env python3
"""
Log viewer for debugging Relevia backend
Usage: python view_logs.py [log_type] [lines]
"""
import sys
import os
from pathlib import Path
from datetime import datetime

def view_logs(log_type="all", lines=50):
    """View recent log entries"""
    logs_dir = Path(__file__).parent / "logs"
    
    if not logs_dir.exists():
        print("❌ No logs directory found. Start the server first to generate logs.")
        return
    
    log_files = {
        "main": "relevia.log",
        "performance": "performance.log", 
        "api": "api.log",
        "gemini": "gemini.log",
        "errors": "errors.log"
    }
    
    if log_type == "all":
        print("📋 Available logs:")
        for name, filename in log_files.items():
            file_path = logs_dir / filename
            if file_path.exists():
                size_kb = file_path.stat().st_size / 1024
                modified = datetime.fromtimestamp(file_path.stat().st_mtime)
                print(f"  {name:12} | {filename:15} | {size_kb:6.1f}KB | {modified.strftime('%H:%M:%S')}")
        
        print(f"\n📖 Recent entries from all logs:")
        # Show recent entries from main log
        main_log = logs_dir / "relevia.log"
        if main_log.exists():
            show_tail(main_log, lines)
        return
    
    if log_type not in log_files:
        print(f"❌ Unknown log type: {log_type}")
        print(f"Available: {', '.join(log_files.keys())}, all")
        return
    
    log_file = logs_dir / log_files[log_type]
    if not log_file.exists():
        print(f"❌ Log file not found: {log_file}")
        return
    
    print(f"📖 Last {lines} lines from {log_type} log:")
    show_tail(log_file, lines)

def show_tail(file_path, lines):
    """Show last N lines of a file"""
    try:
        with open(file_path, 'r') as f:
            # Read all lines and get the last N
            all_lines = f.readlines()
            tail_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            for line in tail_lines:
                # Color code different log levels
                if "ERROR" in line:
                    print(f"\033[91m{line.rstrip()}\033[0m")  # Red
                elif "WARNING" in line:
                    print(f"\033[93m{line.rstrip()}\033[0m")  # Yellow  
                elif "SLOW" in line:
                    print(f"\033[95m{line.rstrip()}\033[0m")  # Magenta
                else:
                    print(line.rstrip())
                    
    except Exception as e:
        print(f"❌ Error reading log file: {e}")

def monitor_logs(log_type="main"):
    """Monitor logs in real-time (like tail -f)"""
    logs_dir = Path(__file__).parent / "logs"
    log_files = {
        "main": "relevia.log",
        "performance": "performance.log", 
        "api": "api.log",
        "gemini": "gemini.log",
        "errors": "errors.log"
    }
    
    if log_type not in log_files:
        print(f"❌ Unknown log type: {log_type}")
        return
        
    log_file = logs_dir / log_files[log_type]
    if not log_file.exists():
        print(f"❌ Log file not found: {log_file}")
        return
    
    print(f"📡 Monitoring {log_type} log (Ctrl+C to stop)...")
    
    try:
        import time
        with open(log_file, 'r') as f:
            # Go to end of file
            f.seek(0, 2)
            
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                    
                # Color code the output
                if "ERROR" in line:
                    print(f"\033[91m{line.rstrip()}\033[0m")  # Red
                elif "WARNING" in line:
                    print(f"\033[93m{line.rstrip()}\033[0m")  # Yellow  
                elif "SLOW" in line:
                    print(f"\033[95m{line.rstrip()}\033[0m")  # Magenta
                else:
                    print(line.rstrip())
                    
    except KeyboardInterrupt:
        print("\n👋 Stopped monitoring logs")
    except Exception as e:
        print(f"❌ Error monitoring logs: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "monitor":
        log_type = sys.argv[2] if len(sys.argv) > 2 else "main"
        monitor_logs(log_type)
    else:
        log_type = sys.argv[1] if len(sys.argv) > 1 else "all"
        lines = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        view_logs(log_type, lines)