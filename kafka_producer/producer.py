import socket
from time import sleep
from json import dumps
from confluent_kafka import Producer
import os
from dotenv import load_dotenv

load_dotenv()

bootstrap_servers = os.getenv("bootstrap_servers")
Port = int(os.getenv("port"))
print(Port)
Topic_Name = os.getenv("topic")
host = os.getenv("host")
print(host)
# Establish socket connection to server
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.connect((host, Port))
server.settimeout(10)

# Kafka Producer configuration
conf = {'bootstrap.servers': bootstrap_servers}
producer = Producer(conf)

def delivery_report(err, msg):
    if err is not None:
        print('Message delivery failed: {}'.format(err))
    else:
        print('Message delivered to {} [{}]'.format(msg.topic(), msg.partition()))

def send_message(message):
    producer.produce(Topic_Name, message.encode('utf-8'), callback=delivery_report)
    producer.flush()

while True:
    try:
        message = server.recv(1024).decode('utf-8')
        send_message(message)
    except socket.timeout:
        print("No messages received in the last 10 seconds.")
    except ConnectionResetError:
        print("Connection reset by peer.")
        break

server.close()
