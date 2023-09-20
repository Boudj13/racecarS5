#!/usr/bin/env python

import socket

from struct import *

HOST = ''
PORT = 65431

# Bind the client socket to any available local address and the chosen port
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
s.bind((HOST, PORT))

try:

    while True:

        data, server_address = s.recvfrom(1024)
        if data:
            x, y, theta, ide = unpack('!fffI', data)
            print(f'RPOS: X={x}, Y={y}, Theta={theta}, ID={ide}')    

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    s.close()

