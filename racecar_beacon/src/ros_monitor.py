#!/usr/bin/env python

import rospy
import socket
import threading
import time
import signal
import sys

from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from tf.transformations import euler_from_quaternion
from struct import *

def quaternion_to_yaw(quat):
    # Uses TF transforms to convert a quaternion to a rotation angle around Z.
    # Usage with an Odometry message: 
    #   yaw = quaternion_to_yaw(msg.pose.pose.orientation)
    (roll, pitch, yaw) = euler_from_quaternion([quat.x, quat.y, quat.z, quat.w])
    return yaw

class ROSMonitor:
    def __init__(self):
        # Add your subscriber here (odom, laserscan):
        self.sub_odom = rospy.Subscriber("/odometry/filtered", Odometry, self.odom_cb)
        self.sub_laser = rospy.Subscriber('/scan', LaserScan, self.laser_cb)

        # Current robot state:
        now = rospy.get_time()
        self.id = 9
        self.pos = [0,0,0]
        self.timer_pos = now
        self.timer_scan = now
        self.obstacle = False
        self.running_pb = True
        self.running_rr = True

        # Params :
        self.remote_request_port = rospy.get_param("remote_request_port", 65432)
        self.pos_broadcast_port  = rospy.get_param("pos_broadcast_port", 65431)

        # Thread for RemoteRequest handling:
        self.rr_thread = threading.Thread(target=self.rr_loop)
        self.rr_thread_exit = threading.Event()

        # Thread for PositionBroadcast handling:
        self.pb_thread = threading.Thread(target=self.pb_loop)
        self.pb_thread_exit = threading.Event()

        self.lock = threading.Lock()

        print("ROSMonitor started.")

    # Subscriber callback:
    def odom_cb(self, msg):
        self.pos[0] = msg.pose.pose.position.x
        self.pos[1] = msg.pose.pose.position.y
        self.pos[2] = quaternion_to_yaw(msg.pose.pose.orientation)
        self.timer_pos = rospy.get_time()
        # print(f'X={self.pos[0]}, Y={self.pos[1]}, Theta={self.pos[2]}')

    def laser_cb(self, msg):
        ranges = msg.ranges

        self.obstacle = False
        for range in ranges:
            if range < 1.0:
                self.obstacle = True
                break
        self.timer_scan = rospy.get_time()
        


    
    # Server diffusion
    def rr_loop(self):
        # Init your socket here :
        rr_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        rr_socket.bind(('10.0.1.21', self.remote_request_port))
        format_RPOS = '!fffI'
        format_OBSF = '!IxxxxxxxxI'
        format_RBID = '!IxxxxxxxxI'
        rr_socket.settimeout(600)  # Set the timeout 

       

        while True: 
            rr_socket.listen(1)
            print('RemoteRequest started.')

            (conn, addr) = rr_socket.accept() # returns new socket and addr. client
            print('RemoteRequest: Connection etablish with ' + str(addr))
            
            while True:
                data = conn.recv(1024) # receive data from client
                if not data: break # stop if client stopped

                if data.decode() == 'RPOS':
                    ecode = 1 if rospy.get_time() - self.timer_pos > 3 else 0
                    enc_send_data = pack(format_RPOS, self.pos[0], self.pos[1], self.pos[2], ecode)
                    conn.send(enc_send_data)

                if data.decode() == 'OBSF':
                    ecode = 1 if rospy.get_time() - self.timer_scan > 3 else 0
                    enc_send_data = pack(format_OBSF, self.obstacle, ecode)
                    conn.send(enc_send_data)        

                if data.decode() == 'RBID':
                    enc_send_data = pack(format_OBSF, self.id, 0)
                    conn.send(enc_send_data)                       

            conn.close() # close the connection
        
        print('RemoteRequest close.')
        rr_socket.unbind(('10.0.1.21', self.remote_request_port))
        
        # loopback the function to restart connexion process
        self.rr_loop()

    def pb_loop(self):
        # Initialize your socket here:
        pb_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        pb_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        pb_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        pb_socket.settimeout(600)  # Set the timeout 

        print('PositionBroadcast started.')

        format = '!fffI'

        while not self.pb_thread_exit.is_set():
            enc_send_data = pack(format, self.pos[0], self.pos[1], self.pos[2], self.id)
            pb_socket.sendto(enc_send_data, ('10.0.1.255', self.pos_broadcast_port))
            print('msg_broadcast')
            time.sleep(1)

        pb_socket.close()
    

    def signal_handler_rr(self, sig, frame):
        self.rr_thread_exit.set()

    def signal_handler_pb(self, sig, frame):
        self.pb_thread_exit.set()


    def start_threads(self):
        self.rr_thread.start()
        self.pb_thread.start()    

if __name__=="__main__":
    rospy.init_node("ros_monitor")

    node = ROSMonitor()

    # Set signal handlers for Ctrl+C in the main thread
    signal.signal(signal.SIGINT, signal.SIG_DFL) 
    
    node.start_threads()

    rospy.spin()

    # Wait for threads to exit gracefully
    node.rr_thread_exit.wait()
    node.pb_thread_exit.wait()








