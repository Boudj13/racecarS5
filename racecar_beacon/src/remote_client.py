#!/usr/bin/env python

import socket

from struct import *

HOST = '10.0.1.21'
PORT = 65432

def handle_rpos(data):
    x, y, theta, ecode = struct.unpack('!fffI', data)
    if ecode == 1:
        return "Data is unavailable"
    return f"RPOS: X={x}, Y={y}, Theta={theta}"

def handle_obsf(data):
    obstacle, ecode = struct.unpack('!IxxxxxxxxI', data)
    if ecode == 1:
        return "Data is unavailable"
    return f"OBSF: Obstacle Present={obstacle}"

def handle_rbid(data):
    robot_id, ecode = struct.unpack('!IxxxxxxxxI', data)
    if ecode == 1:
        return "Data is unavailable"
    return f"RBID: Robot ID={robot_id}"

def switch_case(command, data):
    switch_dict = {
        'RPOS': handle_rpos,
        'OBSF': handle_obsf,
        'RBID': handle_rbid,
    }
    handler = switch_dict.get(command, lambda _: "Invalid command")
    return handler(data)

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    print("Connected")

    while True:
        msg = input("Enter your message (type 'close' to exit): ")

        if msg == 'close':
            s.close()  # Close the connection
            print("Connection closed.")
            break

        # Send the user input to the server
        s.send(msg.encode())

        # Receive the response
        data = s.recv(1024)

        if not data:
            print("Server closed the connection.")
            break

        print(switch_case(msg,data))  # Print the result

except ConnectionRefusedError:
    print("Connection refused. Make sure the server is running and the IP/port are correct.")

except Exception as e:
    print(f"An error occurred: {e}")

