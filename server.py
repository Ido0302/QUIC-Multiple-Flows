import socket
import struct
import threading
import time
import random
import argparse
import os
import queue

PORT = 5000
HOST = "127.0.0.1"

class QuicServer:
    """
    Class representing a QUIC server that sends files to a client.

    Attributes:
        number_of_files (int): The number of files to send to the client.
        server_socket (socket.socket): The server's socket object used for listening and accepting connections.
        connection (socket.socket): The client's socket object used for communication after a connection is accepted.
        client_address (tuple): The address of the connected client.
    """

    def __init__(self, addr, number_of_files):
        """
        Initializes the server, binds it to the specified address, and prepares it to listen for incoming connections.

        Args:
            addr (tuple): The address to bind the server to (host, port).
            number_of_files (int): The number of files the server will send to the client.
        """
        print("Starting server...")
        self.number_of_files = number_of_files
        self.lock = threading.Lock()

        # Create a TCP/IP socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bind the socket to the address
        self.server_socket.bind(addr)
        # Listen for incoming connections
        self.server_socket.listen(3)

    def set_up_server(self):
        """
        Sets up the server to accept a connection and send the number of files to the client.

        This method waits for a client to connect, sends the number of files to the client,
        and receives a confirmation from the client that it has received the number of files.
        """
        # Accept a connection from a client
        self.connection, self.client_address = self.server_socket.accept()

        print("Client connected...sending number of files the client should expect")
        # Send the number of files to the client
        self.connection.send(f"{self.number_of_files}".encode())
        print("Sent it, now we will wait for the client to send it back so we can start...")
        # Receive the number of files back from the client to confirm
        number = self.connection.recv(1024)
        if int(number.decode()) != self.number_of_files:
            print("Problem here...")

    def send_file(self, start_time_of_sending, package_size, file_path, id_stream, result):
        """
        Sends a file to the connected client in chunks of the specified package size.

        Args:
            start_time_of_sending (float): The start time for sending the file, used for performance statistics.
            package_size (int): The size of each package to send.
            file_path (str): The path to the file to send.
            id_stream (int): The stream identifier for the file transfer.
            result (queue.Queue): A queue to store statistics about the file transfer.
        """
        print(f"Starting stream number {id_stream} package size: {package_size}")
        sum_bytes = 0  # Sum of bytes sent

        # Open the file and read its data
        with open(file_path, "rb") as file:
            file_data = file.read()

        total_length = len(file_data)  # Total length of the file data
        num_packages = (total_length + package_size - 1) // package_size  # Number of packages to send

        time_until_sending = time.time() - start_time_of_sending  # For more precise statistics
        # Send the file in packages
        for i in range(num_packages):
            package = file_data[i * package_size: (i + 1) * package_size]  # Get the next package of data
            header = struct.pack("!iii", id_stream, len(package), i)  # Create the header with stream ID and package length
            with self.lock:
                self.connection.send(header)
                self.connection.send(package)  # Send the packet to the client
            sum_bytes += len(package)  # Update the sum of bytes sent

        total_time_in_sec = time.time() - start_time_of_sending  # Total time taken to send the file
        avg_bytes_per_sec = sum_bytes / (total_time_in_sec - time_until_sending) if (total_time_in_sec - time_until_sending) > 0 else 0  # Average bytes per second
        avg_packages_per_sec = num_packages / (total_time_in_sec - time_until_sending) if (total_time_in_sec - time_until_sending) > 0 else 0  # Average packages per second

        with self.lock:
            self.connection.send(struct.pack("!iii", id_stream, 0, 0))  # Send an end-of-file marker

        # Store the statistics of this file transfer in the result queue
        result.put((file_path, sum_bytes, num_packages, avg_bytes_per_sec, avg_packages_per_sec, total_time_in_sec, time_until_sending))

    def close(self, statistic):
        """
        Closes the server socket and prints detailed statistics of the file transfers.

        Args:
            statistic (list): A list of tuples containing file transfer statistics.
        """
        sum_bytes = 0
        sum_packages = 0
        total_time = 0
        print("*****************************************************************************************************************************************************")
        # Calculate total statistics
        for file_stat in statistic:
            sum_bytes += file_stat[1]
            sum_packages += file_stat[2]
            if file_stat[5] > total_time:
                total_time = file_stat[5]
            print("*****************************************************************************************************************************************************")
            print(f"File: {file_stat[0]}, Bytes: {file_stat[1]}, Packages: {file_stat[2]}, Speed (bytes/sec): {file_stat[3]}, Speed (packages/sec): {file_stat[4]} Exact sending time: {file_stat[6]}")
            print("*****************************************************************************************************************************************************")

        if total_time > 0:
            avg_bytes_per_sec = sum_bytes / total_time
            avg_packages_per_sec = sum_packages / total_time
        else:
            avg_bytes_per_sec = avg_packages_per_sec = 0
        print("*****************************************************************************************************************************************************")
        print("Final stats for this file transfer:")
        print(f"Speed total (bytes/sec): {avg_bytes_per_sec}, Speed total (packages/sec): {avg_packages_per_sec}, Total time: {total_time}")
        print("*****************************************************************************************************************************************************")

        # Close the server socket
        self.server_socket.close()

def create_document(file_path, size_mb):
    """
    Creates a binary file with random content of the specified size.

    Args:
        file_path (str): The name of the file to create.
        size_mb (int): The size of the file in megabytes.

    Returns:
        str: The path of the created file.
    """
    size_bytes = int(size_mb) * 1024 * 1024  # Convert size from MB to bytes
    file_name = os.path.join('files_to_send', file_path + ".bin")  # Construct the file name with path
    # Create the file with random binary content
    with open(file_name, 'wb') as file:
        file.write(os.urandom(size_bytes))

    print(f"Document created: {file_path}.bin")
    return file_name

if __name__ == "__main__":
    # Argument parser setup
    arg_parser = argparse.ArgumentParser(description='A file transfer Server to a client.')

    arg_parser.add_argument('-p', '--port', type=int, default=PORT, help='The port to listen on.')
    arg_parser.add_argument('-H', '--host', type=str, default=HOST, help='The host to listen on.')
    arg_parser.add_argument("files", nargs="*", help="File paths to send")

    args = arg_parser.parse_args()

    addr = (args.host, args.port)
    files = args.files

    sum_of_files = len(files)
    if sum_of_files < 1:
        while True:
            print("*** Did not receive file paths, let's create example files to send to the client ***")
            sum_of_files = int(input("Enter the number of files you would like to create: "))
            if sum_of_files > 0:
                if not os.path.exists('files_to_send'):
                    os.makedirs('files_to_send')
                for i in range(sum_of_files):
                    name = input(f"Enter name for the {i+1} file: ")
                    size = int(input(f"Enter size for the {i+1} file in MB: "))
                    files.append(create_document(name, size))
                break
            else:
                print("Problem with your input, let's try again.")

    statistic = []  # List to store statistics of all file transfers
    result = queue.Queue()  # Queue to receive file transfer statistics from threads
    server_sock = QuicServer(addr, sum_of_files)  # Initialize the server
    server_sock.set_up_server()
    threads = []

    start_time_of_sending = time.time()  # Start time for sending the file
    # Create and start a thread for each file to send
    for i, file_path in enumerate(files):
        package_size = random.randint(1000, 2000)
        send_file_thread = threading.Thread(target=server_sock.send_file, args=(start_time_of_sending, package_size, file_path, i, result))
        threads.append(send_file_thread)
        send_file_thread.start()

    # Wait for all threads to finish
    for t in threads:
        t.join()

    # Collect statistics from the result queue
    while not result.empty():
        statistic.append(result.get())

    # Close the server and print final statistics
    server_sock.close(statistic)
