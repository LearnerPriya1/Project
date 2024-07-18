from confluent_kafka import Consumer, KafkaException
from pymongo import MongoClient
from json import loads
import os
from dotenv import load_dotenv

load_dotenv()

bootstrap_servers = os.getenv("bootstrap_servers")
mongouri = os.getenv("MONGO_DB_URL")
topic_name = os.getenv("topic")
database=os.getenv("database")
collection=os.getenv("Device_data")

# MongoDB setup
conn = MongoClient(mongouri)
database = conn[database]
collection = database[collection]

# Kafka consumer configuration
conf = {
    'bootstrap.servers': bootstrap_servers,
    'group.id': 'group_id',
    'auto.offset.reset': 'earliest'
}

# Create Consumer instance
consumer = Consumer(conf)

# Subscribe to topic
consumer.subscribe([topic_name])

# Function to handle messages
def handle_message(msg):
    try:
        data = loads(msg.value().decode('utf-8'))
        collection.insert_one(data)
        print(f"{data} added to {collection}")
    except Exception as e:
        print(f"Error: {e}")

# Poll for new messages and handle them
try:
    while True:
        msg = consumer.poll(timeout=1.0)
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaException._PARTITION_EOF:
                # End of partition event
                print(f"{msg.topic()} [{msg.partition()}] reached end at offset {msg.offset()}")
            elif msg.error():
                raise KafkaException(msg.error())
        else:
            handle_message(msg)
except KeyboardInterrupt:
    pass
finally:
    # Close the consumer
    consumer.close()
