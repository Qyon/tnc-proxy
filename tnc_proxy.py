#!/usr/bin/python
# -*- coding: utf-8 -*-
# author: Tomasz SQ5T
import argparse
import socket
import threading
import logging
import sys
import time

logger = logging.getLogger()

logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s: [%(levelname)7s][%(process)5d][%(processName)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class TNCProxy(object):
    listen_address = "0.0.0.0"
    listen_port = 8002  # listen port

    destination_address = "127.0.0.1"  # connect to IP
    destination_port = 8001  # connect to port
    list_of_clients = []

    def __init__(self, listen_address="0.0.0.0", listen_port=8002, destination_address="127.0.0.1",
                 destination_port=8001):
        """

        :type destination_port: int
        :type destination_address: str
        :type listen_port: int
        :type listen_address: str
        """
        super(TNCProxy, self).__init__()
        self.destination_port = destination_port
        self.destination_address = destination_address
        self.listen_port = listen_port
        self.listen_address = listen_address

    def cli_msg(self, conn):
        peer_info = conn.getpeername()
        logging.info("Client message handler start for %s:%s" % peer_info)
        while True:
            try:
                message = conn.recv(1024)
                if message:
                    peer_info = conn.getpeername()
                    logging.info("New message %s received from %s:%s" % (
                        self.format_for_print(message), peer_info[0], peer_info[1]))
                    self.broadcast(message, conn)
                else:
                    logging.info("No message received from %s:%s. Closing connection" % peer_info)
                    self.remove(conn)
                    return
            except Exception as e:
                logging.info(
                    "Exception occured while receiving from %s:%s. Exception %s" % (peer_info[0], peer_info[1], e))
                self.remove(conn)
                return

    # broadcast message to all connected clients
    def broadcast(self, message, connection):
        for client in self.list_of_clients:
            if client != connection:
                try:
                    peer_info = client.getsockname()
                    logging.info("Sending message %s to %s:%s" % (
                        self.format_for_print(message), peer_info[0], peer_info[1]))
                    client.send(message)
                except:
                    client.close()
                    self.remove(client)
                    return

    def format_for_print(self, message):
        return "".join([c if c.isalnum() else "%%%02x" % ord(c) for c in message])

    # remove connection
    def remove(self, connection):
        connection.close()
        if connection in self.list_of_clients:
            self.list_of_clients.remove(connection)

    def run(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                s.connect((self.destination_address, self.destination_port))
                break
            except socket.error as e:
                logging.error(
                    'Error while connecting to %s:%s: %s' % (self.destination_address, self.destination_port, e))
                time.sleep(5)

        self.add_client(s)

        thread = threading.Thread(target=self.cli_msg, args=(s,))
        thread.daemon = True
        thread.start()

        cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cli.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        cli.bind((self.listen_address, self.listen_port))  # start listening
        logging.info("Starting listening on %s:%s" % (self.listen_address, self.listen_port))
        cli.listen(2)  # max waiting connection
        logging.info("Waiting for connections")
        while True:
            conn, address = cli.accept()  # accept connection from client
            logging.info("New connection")
            conn.setblocking(True)
            self.add_client(conn)  # add client to array of clients
            thread_client = threading.Thread(target=self.cli_msg, args=(conn,))
            thread_client.daemon = True
            thread_client.start()

    def add_client(self, s):
        """

        :type s: socket._socketobject
        """
        peer_info = s.getpeername()
        logging.info("New client connected %s:%s" % peer_info)
        self.list_of_clients.append(s)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen_ip", type=str, dest='listen_address', default=TNCProxy.listen_address)
    parser.add_argument("--listen_port", type=int, default=TNCProxy.listen_port)
    parser.add_argument("--connect_ip", type=str, dest='destination_address', default=TNCProxy.destination_address)
    parser.add_argument("--connect_port", type=int, dest='destination_port', default=TNCProxy.destination_port)
    args = parser.parse_args()

    proxy = TNCProxy(**vars(args))
    proxy.run()
