import requests
from mcstatus import MinecraftServer
from threading import Thread
from queue import Queue
from time import sleep

# Shodan API Key
API_KEY = ""

# Max amount of pages to scan (1 page = 100 servers)
MAX_PAGE = 5

# Version of minecraft to scan for (blank for all)
VERSION = "1.16.4"

# Country codes
COUNTRY_CODES = "AU,NZ" # blank for all


def get_server_batch(query, page_number):
    ''' Get list of servers from Shodan '''
    responce = []

    while responce == []:
        r = requests.get("https://api.shodan.io/shodan/host/search?key="+API_KEY+"&query="+query+"&page="+str(page_number))
        try:
            responce = r.json()["matches"]       
        except KeyError:
            print(f"Error: {r.json()} | Retying")
            sleep(5)
    
    servers = []
    for server in responce:
        servers.append(server["ip_str"])

    return servers

def get_server_stats(ip):
    ''' Returns status if server is up and has players online '''
    ms = MinecraftServer.lookup(ip)

    try: 
        status = ms.status()
        if status.players.online > 0:
            # TODO: Check for whitelist
            return (ip, status)

    except Exception: #  sock timeout (server offline)
        pass

    return False

def display_server(ip, status):
    ''' Print out server info nicely '''
    description_max = 12
    description = status.description['text'][:description_max] + '...'


    rows = []
    rows.append(f' {ip} | {status.players.online}/{status.players.max}') 
    rows.append(f' {status.version.name} {description}')

    container_length = 0
    for row in rows:
        if len(row) > container_length:
            container_length = len(row) + 3

    text = "." + '_'*container_length + ".\n"
    for row in rows:
        new_line = f'| {row}'
        spaces_till_end = (container_length+1) - len(new_line)
        text += new_line + ' '*spaces_till_end + '|\n'
    text += '|' + '_'*container_length + '|'

    print(text)

def scan(server_batch):
    threads = []
    que = Queue() 

    for ip in server_batch:

        threads.append(Thread(
            target=lambda q,
            arg1: q.put(get_server_stats(arg1)),
            args=(que, ip)))
    
    # start threads
    for thread in threads:
        thread.start()

    # join threads
    for thread in threads:
        thread.join()

    while not que.empty():
        try:
            ip, status = que.get()
        except TypeError: # not good server
            continue
    
        display_server(ip, status)
        if que.empty():
            print(f'=====================')
            return False
        
        responce = input('enter to continue (type r to rescan):')
        if responce.lower() == "r":
            print('rescanning...')
            return True
    
    return False

if __name__ == "__main__":
    query = 'port:25565'
    if COUNTRY_CODES:
        COUNTRY_CODES = COUNTRY_CODES.replace(' ', '')
        query += f'+country:{COUNTRY_CODES}'

    if VERSION:
        query += f'+{VERSION}'

    print('Scanning with these options:')
    print("   VERSION:",VERSION)
    print("   COUNTRY CODES:",COUNTRY_CODES)
    print("   MAX SCANS (x100 ip's):",COUNTRY_CODES)

    for i in range(1, MAX_PAGE): # Page range for Shodan.io
        print(f'\n===== Loading Batch {i} =====')
        servers = get_server_batch(query, i)

        while True:
            rescan = scan(servers)
            if not rescan:
                break
