# based on python-flask-docker-sklearn-template
# from classify_view import classify_view
from detector import Detector
# from flask import request
# from flask import Flask
import urllib.request
import numpy as np
import websockets
import threading
import datetime
import psycopg2
import asyncio
import logging
import queue
import json
import time
import cv2
import os

logging.basicConfig(format = '%(asctime)s %(message)s',
                    datefmt = '%m/%d/%Y %H:%M:%S',
                    level=logging.DEBUG)

model_path = os.environ['MODEL']
labels_path = os.environ['LABELS']
gpu_memory = float(os.environ['GPU_MEMORY'])
min_conf = float(os.environ['MIN_CONF'])  # minimum confidence score
W = int(os.environ['W'])
H = int(os.environ['H'])

# app = Flask(__name__)

DB_NAME = os.environ['DB_NAME']
DB_USER = os.environ['DB_USER']
DB_PASS = os.environ['DB_PASS']
DB_DOMAIN = os.environ['DB_DOMAIN']
DB_PORT = os.environ['DB_PORT']

detector = Detector(model_path=model_path, labels_path=labels_path, memory=gpu_memory, H=H, W=W, minimum_confidence=min_conf)
print('detector created', detector)

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

                            print('pre', brokerage['id'].split(':')[0])

                            location = (brokerage['id'].split(':')[0])  # some camera name contains synthetic view name which sometimes is wrong so we get rid of that
                            print('post', location)
                            dt = data['timeseries']['value']['time']
                            url = data['timeseries']['value']['data']
                            url = url.replace('public', uo_url)
                            url_queue.put({'location': location, 'datetime': dt, 'url': url})

class Counting(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global url_queue
        DB_NAME = os.environ['DB_NAME']
        DB_USER = os.environ['DB_USER']
        DB_PASS = os.environ['DB_PASS']
        DB_DOMAIN = os.environ['DB_DOMAIN']
        DB_PORT = os.environ['DB_PORT']
        IP = os.environ['IP']

        conn = psycopg2.connect(host=DB_DOMAIN, port=DB_PORT, user=DB_USER, password=DB_PASS, database=DB_NAME)
        cursor = conn.cursor()
        sqlite_insert_counts_with_param = "INSERT INTO stills_counts VALUES (%s, %s, %s, %s);"
        sqlite_insert_counts_and_dets_with_param_dets = """INSERT INTO stills_counts_dets VALUES (%s, %s, %s, %s, %s);"""

        while True:
            try:
            # if True:
                while True:
                    time.sleep(0.01)
                    if not url_queue.empty():
                        msg = url_queue.get()
                        loc, dt, url = msg['location'], msg['datetime'], msg['url']

                        resp = urllib.request.urlopen(url)
                        img = np.asarray(bytearray(resp.read()), dtype="uint8")
                        img = cv2.imdecode(img, cv2.IMREAD_COLOR)
                        img = cv2.cvtColor(img.copy(), cv2.COLOR_BGR2RGB)
                        img = cv2.resize(img, (W, H))

                        counts, dets = get_prediction(img)
                        # try:
                        # cluster = clustering(url, img)
                        # print('[CLUSTER]', cluster)
                        # except:
                        #     pass
                        print(counts, dets)
                        counts = str(counts).replace("'", '"')
                        dets = str(dets).replace("'", '"')

                        data_tuple = [loc, url, str(dt), counts]
                        print('data tuple', data_tuple)
                        cursor.execute(sqlite_insert_counts_with_param, data_tuple)
                        conn.commit()

                        data_tuple2 = [loc, url, str(dt), counts, dets]
                        print('tuple2', data_tuple2)
                        cursor.execute(sqlite_insert_counts_and_dets_with_param_dets, data_tuple2)
                        conn.commit()
            except Exception as e:
               print('[ERROR] {}'.format(e))
               time.sleep(1)
               pass

# def clustering(url, img):
#     url = url.replace('\\','/')
#     cam = url.split('/')[-3]
#     # dt = url.split('/')[-2]
#     # tm = url.split('/')[-1].split('.')[0]
#     model_name = 'clusterimages-'+cam+'.model'
#     model_path = os.path.join('/ntk38/models', model_name)
#     cluster = classify_view(model_path, img)
#     print('[cluster]', cluster)
#     return cluster

def get_prediction(img):
    detections = detector.detect(img)

    counts = {}
    for det in detections:
        if det[0] in counts:
            counts[det[0]] += 1
        else:
            counts[det[0]] = 1

    dets = {}
    for det in detections:
        if det[0] in dets:
            dets[det[0]].append(det[1])
        else:
            dets[det[0]] = [det[1]]

    return counts, dets

if __name__ == '__main__':
    url_queue = queue.Queue()
    counter = Counting()
    counter.start()

    asyncio.get_event_loop().run_until_complete(wsListener())
    counter.join()
