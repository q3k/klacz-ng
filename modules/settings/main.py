import pika, json

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
config = open("./settings.json").read()

def dispatch(request_type, data, channel):
    if request_type == "get-settings":
        print "publishing settings"

        response = {}
        response["msgType"] = "data"
        response["payload"] = json.loads(config)

        channel.basic_publish(exchange='',
                              routing_key='klacz.info',
                              body = json.dumps(response))

def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
    except:
        return

    if data.has_key("msgType"):
        dispatch(data["msgType"], data, ch)

channel.queue_declare(queue='klacz.info')
channel.basic_consume(callback, queue='klacz.info', no_ack=True)
channel.start_consuming()
