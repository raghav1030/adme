import amqp from 'amqplib';

const RABBITMQ_URL = process.env.RABBITMQ_URL || 'amqp://guest:guest@localhost:5672';
const QUEUE_NAME = 'event_summary_queue';

let channel: any = null;

async function getRabbitChannel() {
    if (channel) return channel;
    const connection = await amqp.connect(RABBITMQ_URL);
    channel = await connection.createChannel();
    await channel.assertQueue(QUEUE_NAME, { durable: true });
    return channel;
}

export async function publishEventToQueue(eventMsg: any) {
    const ch = await getRabbitChannel();
    ch.sendToQueue(QUEUE_NAME, Buffer.from(JSON.stringify(eventMsg)), { persistent: true });
}
