import json
from os import getenv

from google.cloud import pubsub_v1

def publish(topic_name, message_dict):
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(getenv('GCP_PROJECT'), topic_name)
    message_future = publisher.publish(topic_path, json.dumps(message_dict).encode())
    message_future.add_done_callback(lambda x: __handle_pubsub_exceptions(topic_name, x))
    return message_future

def __handle_pubsub_exceptions(topic, message_future):
    # When timeout is unspecified, the exception method waits indefinitely.
    if message_future.exception(timeout=10):
        print('Publishing message on {} threw an Exception {}.'.format(
            topic, message_future.exception()))
