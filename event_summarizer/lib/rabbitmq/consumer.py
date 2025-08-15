import pika
import json

# from langgraph.graph import run_workflow
from db.db import mark_event_done, mark_event_error
import logging

RABBITMQ_URL = "amqp://guest:guest@localhost:5672/"
QUEUE_NAME = "event_summary_queue"


def on_message(ch, method, properties, body):
    print(body)
    event_msg = json.loads(body)
    event_id = event_msg["event_id"]
    print(f"Received event {event_id} from queue")

    try:
        # Optionally, fetch full event from DB if needed
        # event_data = fetch_event(event_id)

        # Run LangGraph workflow with enriched event message
        # summary_result = run_workflow(event_msg)

        # Store summary & mark done asynchronously
        # mark_event_done(event_id, summary_result)

        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"Processed event {event_id} successfully")
    except Exception as e:
        # logging.error(f"Failed to process event {event_id}: {e}")
        # mark_event_error(event_id)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def start_worker():
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_qos(prefetch_count=5)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=on_message)
    print("Waiting for messages...")
    channel.start_consuming()
