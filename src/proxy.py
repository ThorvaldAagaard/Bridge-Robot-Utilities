import socket
import threading
from queue import Queue

def forward_data(src_port, dest_host, dest_port, message_queue, response_queue, exit_event):
    src_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    src_socket.bind(("localhost", src_port))
    src_socket.listen(1)

    while not exit_event.is_set():
        client_conn, _ = src_socket.accept()

        dest_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dest_socket.connect((dest_host, dest_port))

        client_thread = threading.Thread(target=forward_data_client, args=(client_conn, dest_socket, message_queue))
        client_thread.start()

    src_socket.close()

def forward_data_client(client_conn, dest_socket, message_queue):
    while True:
        client_data = client_conn.recv(4096)
        if not client_data:
            break
        
        lines = client_data.decode().split('\n')
        for line in lines:
            if line.strip():  # Skip empty lines
                message_queue.put((dest_socket, line))

def send_data(message_queue, response_queue, exit_event):
    while not exit_event.is_set():
        dest_socket, line = message_queue.get()
        if line is None:
            break

        print(dest_socket.getsockname()[1], " Sending: ", line)
        dest_socket.sendall(line.encode())  # Encode the string to bytes

        response = dest_socket.recv(4096)
        if response:
            print(dest_socket.getsockname()[1], " Received response: ", response.decode())
            response_queue.put(response.decode())

def receive_responses(dest_host, dest_port, response_queue, exit_event):
    dest_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    dest_socket.connect((dest_host, dest_port))

    while not exit_event.is_set():
        response = dest_socket.recv(4096)
        if response:
            print(dest_socket.getsockname()[1], " Received response: ", response.decode())
            response_queue.put(response.decode())

    dest_socket.close()

def main():
    dest_host = "localhost"
    dest_port = 2010

    message_queue = Queue()
    response_queue = Queue()

    exit_event = threading.Event()

    threads = []

    sender_thread = threading.Thread(target=send_data, args=(message_queue, response_queue, exit_event))
    sender_thread.start()

    receiver_thread = threading.Thread(target=receive_responses, args=(dest_host, dest_port, response_queue, exit_event))
    receiver_thread.start()

    for src_port in range(2000, 2005):
        thread = threading.Thread(target=forward_data, args=(src_port, dest_host, dest_port, message_queue, response_queue, exit_event))
        thread.start()
        threads.append(thread)

    # Allow some time for the threads to start
    input("Press Enter to exit...")

    exit_event.set()  # Signal threads to exit

    for thread in threads:
        thread.join()

    sender_thread.join()
    receiver_thread.join()

if __name__ == "__main__":
    main()
