import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import socks
import socket
import threading

proxy_sources = {
    "HTTP/HTTPS": [
        {"url": "https://www.sslproxies.org/", "type": "http"},
        {"url": "https://free-proxy-list.net/", "type": "http"},
        {"url": "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt", "type": "http"},
    ],
    "SOCKS4": [
        {"url": "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt", "type": "socks4"},
        {"url": "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks4.txt", "type": "socks4"},
    ],
    "SOCKS5": [
        {"url": "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt", "type": "socks5"},
        {"url": "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt", "type": "socks5"},
    ]
}

headers = {'User-Agent': 'Mozilla/5.0'}
file_lock = threading.Lock()

def fetch_proxies(name, url, proxy_type):
    print(f"collecting  {proxy_type.upper()} from {url}")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        proxies = []
        if "txt" in url:
            lines = response.text.strip().splitlines()
            proxies = [line.strip() for line in lines if line.strip()]
        else:
            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table", attrs={"id": "proxylisttable"})
            if table:
                for row in table.tbody.find_all("tr"):
                    cols = row.find_all("td")
                    ip = cols[0].text.strip()
                    port = cols[1].text.strip()
                    proxies.append(f"{ip}:{port}")

        print(f"received {len(proxies)} {proxy_type.upper()} proxies")
        return [(p, proxy_type) for p in proxies]

    except Exception as e:
        print(f"connection failed for {proxy_type.upper()} source ({url}): {e}")
        return []

def save_proxy(proxy_type, proxy):
    formatted_proxy = f"{proxy}:{proxy_type}"
    with file_lock:
        with open("valid_proxies.txt", "a") as f:
            f.write(formatted_proxy + "\n")

def test_proxy(proxy_info):
    proxy, proxy_type = proxy_info
    if ':' not in proxy:
        return
    try:
        ip, port = proxy.strip().split(":")
        port = int(port)
    except ValueError:
        return

    try:
        if proxy_type == "http":
            r = requests.get("http://httpbin.org/ip", proxies={
                "http": f"http://{proxy}",
                "https": f"http://{proxy}"
            }, timeout=5)
            if r.status_code == 200:
                print(f"[HTTP oK] {proxy}")
                save_proxy(proxy_type, proxy)

        elif proxy_type in ["socks4", "socks5"]:
            sock_type = socks.SOCKS4 if proxy_type == "socks4" else socks.SOCKS5
            s = socks.socksocket()
            s.set_proxy(sock_type, ip, port)
            s.settimeout(5)
            s.connect(("httpbin.org", 80))
            s.send(b"GET /ip HTTP/1.1\r\nHost: httpbin.org\r\n\r\n")
            s.recv(1024)
            s.close()
            print(f"[{proxy_type.upper()} oK] {proxy}")
            save_proxy(proxy_type, proxy)

    except:
        pass

def main():
    all_proxies = []
    for name, sources in proxy_sources.items():
        for source in sources:
            proxies = fetch_proxies(name, source["url"], source["type"])
            all_proxies.extend(proxies)

    print(f"\n[iNFO] testing {len(all_proxies)} proxies...")

    with ThreadPoolExecutor(max_workers=50) as executor:
        executor.map(test_proxy, all_proxies)

    print("\ncompleted.")

if __name__ == "__main__":
    main()
