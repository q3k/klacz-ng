import pika, json, md5

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()
channel.exchange_declare(exchange='logs',type='fanout')
result = channel.queue_declare(exclusive=True)
queue_name = result.method.queue
channel.queue_bind(exchange='klacz.events',queue=queue_name)

resp_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
resp_channel = resp_connection.channel()
resp_channel.queue_declare(queue='klacz.responses')


def hash_word(word):
    m = md5.new()
    m.update(word.encode('utf-8'))
    return m.hexdigest()

def sort_by_hash(words):
    result = map(lambda x: (x, hash_word(x)), words)
    return map(lambda x: x[0], sorted(result, key=lambda elem: elem[1]))

def try_to_pick(user, string):
    words = string.split(' ')

    if words == "":
        return

    if words[0] != ",pick":
        return

    sorts = sort_by_hash(words[1:])
    resp_channel.basic_publish(exchange='',
                               routing_key='klacz.responses',
                               body=json.dumps({ "to" : user,
                                                 "message" : ' < '.join(sorts)}))

def callback(ch, method, properties, body):
    print body
    data = json.loads(body)
    body = data["payload"]["body"]
    user = data["payload"]["from"]
    try_to_pick(user, body)

channel.basic_consume(callback,
                      queue=queue_name,
                      no_ack=True)

channel.start_consuming()
