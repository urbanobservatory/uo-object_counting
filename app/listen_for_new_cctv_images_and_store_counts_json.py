import websockets
import threading
import requests
import psycopg2
import datetime
import asyncio
import sqlite3
import queue
import json
import time
import os


async def wsListener():
    global url_queue
    url = 'wss://api.newcastle.urbanobservatory.ac.uk/stream'
    uo_url = 'https://file.newcastle.urbanobservatory.ac.uk'
    async with websockets.connect(url) as websocket:
        while True:
            time.sleep(0.01)
            msg = await websocket.recv()
            msg = json.loads(msg)
            if "data" in msg:
                data = msg['data']
                # print(data)
                if "brokerage" in data:
                    brokerage = data['brokerage']
                    if "broker" in brokerage:
                        broker = brokerage['broker']
                        if broker['id'] == "UTMC Open Camera Feeds":
                            # print(msg)
                            location = (brokerage['id'].split(':')[0])  # some camera name contains synthetic view name which sometimes is wrong so we get rid of that
                            dt = data['timeseries']['value']['time']
                            url = data['timeseries']['value']['data']
                            url = url.replace('public', uo_url)
                            url_queue.put({'location': location, 'datetime': dt, 'url': url})


class CarCountingAPI(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global url_queue
        # db = os.environ['DB']
        DB_NAME = os.environ['DB_NAME']
        DB_USER = os.environ['DB_USER']
        DB_PASS = os.environ['DB_PASS']
        DB_DOMAIN = os.environ['DB_DOMAIN']
        DB_PORT = os.environ['DB_PORT']
        IP = os.environ['IP']

        # conn = sqlite3.connect(db)
        conn = psycopg2.connect(host=DB_DOMAIN, port=DB_PORT, user=DB_USER, password=DB_PASS, database=DB_NAME)
        cursor = conn.cursor()
        # print(conn, cursor)
        # check_if_table_exists = "SELECT name FROM sqlite_master WHERE type='table' AND name='stills_counts';"
        # cursor.execute(check_if_table_exists)
        # recs = cursor.fetchall()
        # table_exists = len(recs)
        # create a table
        # if table_exists == 0:
        #     cursor.execute("""CREATE TABLE stills_counts(location text, url text, datetime timestamp, counts json)""")
        # sqlite_insert_with_param = """INSERT INTO 'stills_counts' ('location', 'url', 'datetime', 'counts') VALUES (?, ?, ?, ?);"""
        sqlite_insert_with_param = "INSERT INTO stills_counts VALUES (%s, %s, %s, %s);"

        port = 80
        if os.environ['ENVIRONMENT'] == 'production':
            port = 80
        if os.environ['ENVIRONMENT'] == 'local':
            port = 5000

        counting_api = 'http://{}:{}/detection/api/v1.0/count_objects'.format(IP, port)
        while True:
            # await asyncio.sleep(0.1)
            time.sleep(0.01)
            if not url_queue.empty():
                try:
                    ask = url_queue.get()
                    url = ask['url']
                    PARAMS = {'img_url': url}
                    r = requests.get(url=counting_api, params=PARAMS)
                    resp = r.text

                    dt = ask['url'].split('/')[-2:]
                    d, t = dt
                    dt = datetime.datetime(int(d[:4]), int(d[4:6]), int(d[6:8]), int(t[:2]), int(t[2:4]), int(t[4:6]))
                    print('ask', ask)
                    print('resp', resp)
                    data_tuple = [ask['location'], ask['url'], str(dt), resp]
                    # print(data_tuple)
                    cursor.execute(sqlite_insert_with_param, data_tuple)
                    conn.commit()

                except Exception as e:
                    print(e)
                    pass

url_queue = queue.Queue(1000)
started = datetime.datetime.now()

counter = CarCountingAPI()
counter.start()

asyncio.get_event_loop().run_until_complete(wsListener())
counter.join()
