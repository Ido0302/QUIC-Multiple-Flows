import socket
import struct
import argparse
import os
import threading

# Constants for default port and host
PORT = 5000
HOST = "127.0.0.1"

class QuicClient:
    """
    A class to represent a QUIC client that connects to a server, receives files, 
    and saves them to disk. It uses multi-threading to handle multiple file streams.
    """

    def __init__(self, addr):
        """
        Initializes the QuicClient instance with the server address and sets up a lock.

        Args:
            addr (tuple): A tuple containing the server IP address and port.
        """
        print("Starting client...")
        self.addr = addr
        self.lock = threading.Lock()  # Initialize a lock to ensure thread-safe operations

    def set_up_client(self):
        """
        Sets up the client by creating a socket, connecting to the server, 
        and receiving the number of files to be transferred.

        The method:
        - Creates a TCP socket.
        - Connects to the server using the provided address.
        - Receives and decodes the number of files from the server.
        """
        # Create a TCP/IP socket
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Connect the socket to the server
        self.client_socket.connect(self.addr)
        print("Connected... receiving the number of files...")
        
        # Receive the number of files from the server
        self.number_of_files = self.client_socket.recv(1024)
        # Decode the received data to get the number of files
        self.number_of_files = int(self.number_of_files.decode())
        print(f"Received number of files: {self.number_of_files}")

    def ready_to_recv(self):
        """
        Sends the number of files to the server to signal readiness to receive the data.

        This method:
        - Encodes the number of files into bytes.
        - Sends this data to the server to indicate that the client is ready to start receiving files.
        """
        self.client_socket.send(str(self.number_of_files).encode())

    def recv_file(self, file_buffers, curret_package):
        """
        Receives files from the server, processes them, and stores them in the provided buffers.

        Args:
            file_buffers (dict): A dictionary mapping stream IDs to bytearrays where file data will be stored.
            curret_package (list): A list tracking the current package ID for each stream to ensure proper ordering.

        This method:
        - Continuously receives data from the server.
        - Processes each data chunk by checking its header and package ID.
        - Writes the data to the correct buffer based on the stream ID and package ID.
        """
        while True:
            with self.lock:  # Acquire the lock to ensure thread-safe operations
                try:
                    # Receive header (12 bytes) containing stream ID, data length, and package ID
                    header = self.client_socket.recv(12)
                    if not header:
                        # Break the loop if no more data is received
                        break
                    # Unpack the header using struct to extract stream ID, data length, and package ID
                    id_stream, data_length, id_package = struct.unpack('!iii', header)
                    
                    # Check if the data length is zero, indicating the end of the stream
                    if data_length == 0:
                        break
                    else:
                        # Receive the actual data based on the data length
                        package = self.client_socket.recv(data_length)
                except Exception as e:
                    # Handle any exceptions that occur during data reception
                    print(f"Exception during receiving data: {e}")
                    break

            # Check if the received stream ID is in the file_buffers
            if id_stream in file_buffers:
                is_curret_package = False
                while not is_curret_package:
                    # Ensure the package ID is in the correct order
                    if curret_package[id_stream] == id_package:
                        curret_package[id_stream] += 1  # Increment the package ID
                        file_buffers[id_stream].extend(package)  # Append the received data to the buffer
                        is_curret_package = True
                        print(f"Writing package stream id: {id_stream}, size: {data_length}, number: {id_package}")

    def wirting_files(self, files, file_buffers):
        """
        Writes the received file data to disk.

        Args:
            files (list): A list of filenames corresponding to the received file streams.
            file_buffers (dict): A dictionary mapping stream IDs to bytearrays containing file data.

        This method:
        - Creates a directory for received files if it does not exist.
        - Iterates through the file buffers and writes each buffer to its corresponding file on disk.
        """
        # Create the directory for received files if it does not exist
        if not os.path.exists('files_recv'):
            os.makedirs('files_recv')

        for id_stream, file_data in file_buffers.items():
            # Create the full path for the file
            file_path = os.path.join('files_recv', files[id_stream])
            # Write the data to the file
            with open(file_path, "wb") as file:
                file.write(file_data)

    def close(self):
        """
        Closes the client socket.
        
        This method:
        - Closes the socket connection to the server to clean up resources.
        """
        self.client_socket.close()

if __name__ == "__main__":
    # Argument parser to handle command-line arguments
    arg_parser = argparse.ArgumentParser(description='A client to receive files from the server.')
    arg_parser.add_argument('-p', '--port', type=int, default=PORT, help='The port to connect to.')
    arg_parser.add_argument('-H', '--host', type=str, default=HOST, help='The host to connect to.')

    args = arg_parser.parse_args()
    addr = (args.host, args.port)

    # Create an instance of QuicClient with the provided address
    client_sock = QuicClient(addr)
    client_sock.set_up_client()

    files = []
    # Create a directory for received files if it does not exist
    if not os.path.exists('files_recv'):
        os.makedirs('files_recv')

    # Get file names from the user
    for i in range(client_sock.number_of_files):
        file_name = input(f"Enter name for the file {i+1} you would like to store the data in: ") + ".bin"
        files.append(file_name)

    recv_threads = []
    # Initialize buffers for each file stream
    file_buffers = {i: bytearray() for i in range(client_sock.number_of_files)}
    curret_package = [0] * client_sock.number_of_files

    # Signal the server that the client is ready to receive files
    client_sock.ready_to_recv()
    # Start a thread for each file stream to receive data concurrently
    for i in range(client_sock.number_of_files):
        recving = threading.Thread(target=client_sock.recv_file, args=(file_buffers, curret_package,))
        recv_threads.append(recving)
        recving.start()

    # Wait for all threads to complete
    for t in recv_threads:
        t.join()

    # Write received data to files
    client_sock.wirting_files(files, file_buffers)

    # Close the client connection
    client_sock.close()
