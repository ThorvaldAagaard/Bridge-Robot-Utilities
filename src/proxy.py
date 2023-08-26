import socket
import threading

def forward_data(src_port, dest_host, dest_port):
    src_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    src_socket.bind(("localhost", src_port))
    src_socket.listen(1)
    
    while True:
        client_conn, _ = src_socket.accept()
        
        dest_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dest_socket.connect((dest_host, dest_port))
        
        client_data = client_conn.recv(4096)
        if not client_data:
            break
        print(client_data)
        dest_socket.sendall(client_data)
        
        dest_data = dest_socket.recv(4096)
        if not dest_data:
            break
        print(dest_data)
        client_conn.sendall(dest_data)
        
        client_conn.close()
        dest_socket.close()

def main():
    dest_host = "localhost"
    dest_port = 2010

    # Start a thread for each source port
    threads = []
    for src_port in range(2000, 2005):  # Adjust the range as needed
        thread = threading.Thread(target=forward_data, args=(src_port, dest_host, dest_port))
        print(src_port, dest_host, dest_port)
        thread.start()
        threads.append(thread)

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()
