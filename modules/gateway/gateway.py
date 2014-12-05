from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log
from threading import Thread
import time, sys, pika, json, atexit

class Settings():
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue='klacz.info')
        self.channel.basic_consume(self.callback, queue='klacz.info', no_ack=True)
        self.response = None

    def callback(self, ch, method, props, body):
        self.response = body

    def getConfig(self):
        self.channel.basic_publish(exchange='',
                                   routing_key='klacz.info',
                                   body=json.dumps({"msgType" : "get-settings"})
        )

        while(self.response == None):
            self.connection.process_data_events()

        return json.loads(self.response)


class LogBot(irc.IRCClient):
    def module_message(self, ch, method, props, body):
        print "[x] got response"
        print body
        j = json.loads(body)
        self.msg(j["to"].encode('ascii'), j["message"].encode('utf-8'))

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)

    def signedOn(self):
        for channel in self.factory.settings["channel"]:
            self.join(channel.encode('ascii'))

    def joined(self, channel):
        pass

    def privmsg(self, user, channel, msg):
        user = user.split('!', 1)[0]
        payload = {
            "from" : user if self.nickname == channel else channel,
            "body" : msg
        }

        message = {
            "msgType" : "privmsg",
            "payload" : payload
        }

        print message

        self.factory.exchange.basic_publish(exchange='klacz.events',
                                    routing_key='',
                                    body=json.dumps(message))

    def action(self, user, channel, msg):
        user = user.split('!', 1)[0]

    def irc_NICK(self, prefix, params):
        old_nick = prefix.split('!')[0]
        new_nick = params[0]

    def alterCollidedNick(self, nickname):
        return nickname + '^'

class LogBotFactory(protocol.ClientFactory):
    def __init__(self, settings):
        self.settings = settings;

    def event_exchange(self):
        self.exchange_connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.exchange = self.exchange_connection.channel()
        self.exchange.exchange_declare(exchange='klacz.events', type='fanout')

    def responses_queue(self):
        self.responses_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.responses_channel = self.responses_connection.channel()
        self.responses_channel.queue_declare(queue='klacz.responses')

    def buildProtocol(self, addr):
        self.event_exchange()
        self.responses_queue()

        p = LogBot()
        p.nickname = self.settings["nickname"].encode('ascii')
        self.responses_channel.basic_consume(p.module_message, queue='klacz.responses', no_ack=True)
        self.thr = Thread(target=lambda : self.responses_channel.start_consuming())
        self.thr.start()
        print "ELO"
        p.factory = self

        return p

    def clientConnectionLost(self, connector, reason):
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()

    def __del__(self):
        channel.close()

if __name__ == '__main__':
    def die():
        print "bye"

    settings = Settings();
    res = settings.getConfig()['payload'];
    factory = LogBotFactory(res)
    reactor.connectTCP(res["server"], 6667, factory)

    print "starting reactor"
    atexit.register(die)
    reactor.run()
