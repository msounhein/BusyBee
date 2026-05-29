#!/usr/bin/env python3
"""
OpenClaw System Monitor
Monitors memory, CPU, and processes every 10 seconds.
Logs to data/monitor.jsonl for analysis.
Auto-restarts gateway if it exceeds a memory threshold.
"""

import psutil
import json
import time
import os
import subprocess
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=-5))
INTERVAL = 10  # seconds
MEMORY_THRESHOLD_MB = 2048  # alert threshold (no auto-restart)
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
LOG_FILE = os.path.join(LOG_DIR, 'monitor.jsonl')

# OpenClaw-related process names to track
OPENCLAW_NAMES = {
    'openclaw-gateway', 'openclaw-gatewa', 'openclaw',
    'mempalace', 'gunicorn',
}

# Other heavy processes to watch
WATCH_NAMES = {
    'chrome', 'plasmashell', 'firefox', 'node', 'python3', 'python',
    'Xorg', 'nxnode.bin', 'nxserver.bin', 'cloudflared',
}


def get_cst_now():
    return datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')


def get_process_info(proc):
    """Safely extract process info."""
    try:
        with proc.oneshot():
            name = proc.name()
            pid = proc.pid
            cpu = proc.cpu_percent()
            mem_info = proc.memory_info()
            cmdline = ' '.join(proc.cmdline()[:3]) if proc.cmdline() else ''
            create_time = proc.create_time()
            return {
                'pid': pid,
                'name': name,
                'cpu_pct': round(cpu, 1),
                'rss_mb': round(mem_info.rss / 1024 / 1024, 1),
                'vms_mb': round(mem_info.vms / 1024 / 1024, 1),
                'cmdline': cmdline[:200],
                'uptime_min': round((time.time() - create_time) / 60, 1),
            }
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return None


def is_openclaw_related(info):
    """Check if a process is OpenClaw-related."""
    if not info:
        return False
    name_lower = info['name'].lower()
    cmdline_lower = info['cmdline'].lower()
    return (
        any(n in name_lower for n in OPENCLAW_NAMES) or
        'openclaw' in cmdline_lower or
        'mempalace' in cmdline_lower or
        'job-tracker' in cmdline_lower or
        'gunicorn' in name_lower
    )


def is_watched(info):
    """Check if a process is worth watching."""
    if not info:
        return False
    name_lower = info['name'].lower()
    return any(n in name_lower for n in WATCH_NAMES)


def collect_snapshot():
    """Collect a full system snapshot."""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    cpu = psutil.cpu_percent(interval=1)

    snapshot = {
        'timestamp': get_cst_now(),
        'system': {
            'cpu_pct': cpu,
            'mem_total_mb': round(mem.total / 1024 / 1024),
            'mem_used_mb': round(mem.used / 1024 / 1024),
            'mem_available_mb': round(mem.available / 1024 / 1024),
            'mem_pct': mem.percent,
            'swap_total_mb': round(swap.total / 1024 / 1024),
            'swap_used_mb': round(swap.used / 1024 / 1024),
            'swap_pct': swap.percent,
        },
        'openclaw': [],
        'heavy_processes': [],
        'top_by_memory': [],
    }

    # Collect all processes
    all_procs = []
    for proc in psutil.process_iter(['pid', 'name']):
        info = get_process_info(proc)
        if info and info['rss_mb'] > 5:  # only processes using > 5MB
            all_procs.append(info)

    # Categorize
    for info in all_procs:
        if is_openclaw_related(info):
            snapshot['openclaw'].append(info)
        if is_watched(info) and info['rss_mb'] > 20:
            snapshot['heavy_processes'].append(info)

    # Top 10 by memory regardless of category
    snapshot['top_by_memory'] = sorted(all_procs, key=lambda x: x['rss_mb'], reverse=True)[:10]

    # Calculate OpenClaw totals
    oc_total = sum(p['rss_mb'] for p in snapshot['openclaw'])
    snapshot['openclaw_total_mb'] = round(oc_total, 1)

    return snapshot


def check_gateway_health(snapshot):
    """Check if gateway needs a restart."""
    gateway_procs = [p for p in snapshot['openclaw'] if 'openclaw-gatewa' in p['name']]
    
    for gw in gateway_procs:
        if gw['rss_mb'] > MEMORY_THRESHOLD_MB:
            return {
                'action': 'restart_gateway',
                'reason': f"Gateway PID {gw['pid']} using {gw['rss_mb']} MB (threshold: {MEMORY_THRESHOLD_MB} MB)",
                'pid': gw['pid'],
            }
    
    return None




def log_event(event):
    """Append a JSON line to the log file."""
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(event) + '\n')


def cleanup_old_logs():
    """Keep only last 24 hours of logs (approx 8640 entries at 10s interval)."""
    if not os.path.exists(LOG_FILE):
        return
    try:
        size = os.path.getsize(LOG_FILE)
        if size > 50 * 1024 * 1024:  # > 50 MB
            # Read last 8640 lines
            result = subprocess.run(
                ['tail', '-n8640', LOG_FILE],
                capture_output=True, text=True, timeout=30
            )
            with open(LOG_FILE, 'w') as f:
                f.write(result.stdout)
    except Exception:
        pass


def main():
    print(f"[{get_cst_now()}] OpenClaw System Monitor started (interval={INTERVAL}s, threshold={MEMORY_THRESHOLD_MB}MB)")
    cycle = 0

    while True:
        try:
            snapshot = collect_snapshot()

            # Check gateway health
            health = check_gateway_health(snapshot)

            log_entry = {
                'ts': snapshot['timestamp'],
                'sys': snapshot['system'],
                'oc_mb': snapshot['openclaw_total_mb'],
                'oc_procs': len(snapshot['openclaw']),
                'top': [{'n': p['name'], 'pid': p['pid'], 'mb': p['rss_mb'], 'cpu': p['cpu_pct']} for p in snapshot['top_by_memory']],
            }

            if health:
                log_entry['alert'] = health
                print(f"[{snapshot['timestamp']}] ⚠️ ALERT: {health['reason']} (logging only, no auto-restart)")

            log_event(log_entry)

            # Print summary every 6 cycles (1 minute)
            cycle += 1
            if cycle % 6 == 0:
                sys = snapshot['system']
                oc = snapshot['openclaw']
                print(
                    f"[{snapshot['timestamp']}] "
                    f"CPU: {sys['cpu_pct']}% | "
                    f"Mem: {sys['mem_used_mb']}/{sys['mem_total_mb']} MB ({sys['mem_pct']}%) | "
                    f"Swap: {sys['swap_used_mb']}/{sys['swap_total_mb']} MB | "
                    f"OpenClaw: {snapshot['openclaw_total_mb']} MB ({len(oc)} procs)"
                )

            # Cleanup logs every 360 cycles (1 hour)
            if cycle % 360 == 0:
                cleanup_old_logs()

        except Exception as e:
            print(f"[{get_cst_now()}] Error: {e}")

        time.sleep(INTERVAL)


if __name__ == '__main__':
    main()
