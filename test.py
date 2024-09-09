
# test.py

import time
import unittest
import server
import queue
import threading
import os
import random
from client import QuicClient
import matplotlib.pyplot as plt
import compareFiles

class TestQuicServerClient(unittest.TestCase):
    """
    Unit test class for testing the QUIC server and client multi-flow implementation.
    This class tests the file transfer process over multiple flows, collects statistics, 
    and generates graphs for data rate (bytes per second) and packet rate (packets per second).
    """

    def test_server_client_multi_flow(self):
        """
        Tests the file transfer process over multiple flows by:
        1. Setting up directories for file sending and receiving.
        2. Initializing server and client instances.
        3. Creating test files and defining random package sizes.
        4. Starting threads for server and client operations.
        5. Collecting and analyzing transfer statistics.
        6. Validating transferred files and plotting performance graphs.
        """

        # Set up directories for sending and receiving files
        folder_sending_name = 'files_to_send'
        folder_recv_name = 'files_recv'
        os.makedirs(folder_sending_name, exist_ok=True)
        os.makedirs(folder_recv_name, exist_ok=True)

        # Define the number of flows and prepare file names and package sizes
        number_of_flows = 10
        size_of_each_file = 6
        files_names = []
        package_sizes = []
        final_statistic = []
        result = queue.Queue()

        # Server and client configuration
        ip = '127.0.0.1'
        port = 5000

        # Initialize server and client
        TcpBaseServer = server.QuicServer((ip, port), number_of_flows)
        client = QuicClient((ip, port))

        # Start server and client setup in separate threads
        t1 = threading.Thread(target=TcpBaseServer.set_up_server)
        t1.start()
        t2 = threading.Thread(target=client.set_up_client)
        t2.start()

        # Create test files and generate random package sizes
        for i in range(number_of_flows):
            filename = f"file{i}"
            files_names.append(filename + ".bin")
            server.create_document(filename, size_of_each_file)  # creates a file
            package_sizes.append(random.randint(1000, 2000))  # Random package size between 1000 and 2000 bytes

        # Start file transfer threads
        threads = []
        client.ready_to_recv()
        file_buffers = {i: bytearray() for i in range(client.number_of_files)}
        curret_package = [0] * client.number_of_files

        start = time.time()
        for i in range(number_of_flows):
            recving = threading.Thread(target=client.recv_file, args=(file_buffers, curret_package,))
            sending_thread = threading.Thread(target=TcpBaseServer.send_file, args=(start, package_sizes[i], f"{folder_sending_name}/{files_names[i]}", i, result))
            threads.append(sending_thread)
            threads.append(recving)
            recving.start()
            sending_thread.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        client.wirting_files(files_names, file_buffers)

        # Collect statistics from the result queue
        while not result.empty():
            final_statistic.append(result.get())

        # Validate the results
        self.assertGreater(len(final_statistic), 0)

        # Compare sent and received files
        for name in files_names:
            self.assertTrue(compareFiles.compare_files(f"{folder_sending_name}/{name}", f"{folder_recv_name}/{name}"))

        # Plot performance graphs

        # Initialize lists to store average rates for final graph and the total sending time
        total_time_flows = 0
        avg_total_bytes_per_sec = [] # for y in graph
        avg_total_packet_per_sec = [] # for y in graph

        # Calculation of the total time of sending
        for stat in final_statistic:
            if stat[5] > total_time_flows:
                total_time_flows = stat[5]

        time_for_graph = [] # for x in graph
        i = 0
        while i < total_time_flows:
            time_for_graph.append(i) # from 0 to total time of sending

            avg_byte = 0 # avg bytes per sec i
            avg_packet = 0 # avg packet per sec i
            activeFlows = 0 # flows that was active at this sec i 
            for stat in final_statistic:
                if i >= stat[6] and i < stat[5]: # if the flow was active at sec i in the total time
                    avg_byte += stat[3]
                    avg_packet += stat[4]
                    activeFlows += 1
            if activeFlows > 0:
                avg_byte /= activeFlows 
                avg_packet /= activeFlows 
            avg_total_bytes_per_sec.append(avg_byte)
            avg_total_packet_per_sec.append(avg_packet)
            i += 1



        # Create a figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

        # Data rate subplot
        ax1.plot(time_for_graph, avg_total_bytes_per_sec, marker='o', linestyle='-', color='b')
        ax1.set_xlabel('time in sec')
        ax1.set_ylabel('Average Data Rate (bytes/sec)')
        ax1.set_title(f'time vs. Average Data Rate :: number of flows is {number_of_flows}')
        ax1.grid(True)

        # Packet rate subplot
        ax2.plot(time_for_graph, avg_total_packet_per_sec, marker='o', linestyle='-', color='r')
        ax2.set_xlabel('time in sec')
        ax2.set_ylabel('Average Packet Rate (packets/sec)')
        ax2.set_title(f'time vs. Average Packet Rate :: number of flows is {number_of_flows}')
        ax2.grid(True)

        # Adjust layout to prevent overlap
        plt.tight_layout()

        # Display the plots
        plt.show()
        
         # Clean up resources
        TcpBaseServer.close(final_statistic)
        client.close()

if __name__ == '__main__':
    unittest.main()
