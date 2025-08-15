from lib.rabbitmq.consumer import start_worker


def main():
    print("Starting event summarizer service...")
    start_worker()


if __name__ == "__main__":
    main()
