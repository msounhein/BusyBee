import os
import json
import psutil
from datetime import datetime

STATUS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'run_status.json')

def load_status():
    if not os.path.exists(STATUS_FILE):
        return {
            'scraper': {'running': False, 'started_at': None, 'finished_at': None, 'result': None, 'error': None},
            'scorer': {'running': False, 'started_at': None, 'finished_at': None, 'result': None, 'error': None},
            'researcher': {'running': False, 'started_at': None, 'finished_at': None, 'result': None, 'error': None}
        }
    try:
        with open(STATUS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {
            'scraper': {'running': False, 'started_at': None, 'finished_at': None, 'result': None, 'error': None},
            'scorer': {'running': False, 'started_at': None, 'finished_at': None, 'result': None, 'error': None},
            'researcher': {'running': False, 'started_at': None, 'finished_at': None, 'result': None, 'error': None}
        }

def save_status(status):
    try:
        os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
        with open(STATUS_FILE, 'w') as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        print(f"Error saving status to {STATUS_FILE}: {e}", flush=True)

def update_process_status(process_name, running=None, started_at=None, finished_at=None, result=None, error=None):
    status = load_status()
    if process_name not in status:
        status[process_name] = {'running': False, 'started_at': None, 'finished_at': None, 'result': None, 'error': None}
    
    if running is not None:
        status[process_name]['running'] = running
        if running:
            # Clear finished details when starting
            status[process_name]['finished_at'] = None
            status[process_name]['result'] = None
            status[process_name]['error'] = None
            
    if started_at is not None:
        status[process_name]['started_at'] = started_at
        
    # Allow explicitly updating to None or values if provided
    # Only skip if the argument was not passed (None default)
    # But since we use kwargs, we can distinguish by checking if they are not None,
    # except when we want to clear them on finish.
    # To be safe: when starting, they are cleared above.
    # When finishing: finished_at/result/error are explicitly passed.
    if finished_at is not None:
        status[process_name]['finished_at'] = finished_at
    if result is not None:
        status[process_name]['result'] = result
    if error is not None:
        status[process_name]['error'] = error
        
    save_status(status)

def is_external_process_running(process_name):
    """Check if there is an external process running the scraper or scorer."""
    for proc in psutil.process_iter():
        try:
            cmd = proc.cmdline()
            cmd_str = ' '.join(cmd) if cmd else ''
            # Exclude current process to avoid false positives
            if proc.pid == os.getpid():
                continue
            if process_name == 'scraper':
                # Match cron script or python scraper scripts, excluding app.py itself
                if 'cron_scraper' in cmd_str or ('scraper' in cmd_str and 'app.py' not in cmd_str):
                    return True
            elif process_name == 'scorer':
                # Match python scorer scripts, excluding app.py itself
                if 'scorer' in cmd_str and 'app.py' not in cmd_str:
                    return True
            elif process_name == 'researcher':
                # Match python build_packets script, excluding app.py itself
                if 'build_packets' in cmd_str and 'app.py' not in cmd_str:
                    return True
        except Exception:
            pass
    return False
