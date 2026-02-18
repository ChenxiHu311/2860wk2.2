#!/usr/bin/env python3

import socket
import argparse
import os
import struct
import sys

BUFFER_SIZE = 1024


# =========================
# Server
# =========================
def run_server(port, outdir):

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("", port))
    server_socket.listen(1)

    print("Server is listening on port", port)

    # Server runs forever
    while True:
        conn, addr = server_socket.accept()
        print("Connected from", addr)

        try:
            # Receive filename length (4 bytes)
            data = conn.recv(4)
            if len(data) < 4:
                conn.close()
                continue

            name_length = struct.unpack("!I", data)[0]

            # Receive filename
            filename_bytes = conn.recv(name_length)
            filename = filename_bytes.decode()

            output_path = os.path.join(outdir, filename + "-received")

            # If file already exists, reject
            if os.path.exists(output_path):
                conn.sendall(b"NO")
                conn.close()
                continue
            else:
                conn.sendall(b"OK")

            # Receive file size (8 bytes)
            size_data = conn.recv(8)
            file_size = struct.unpack("!Q", size_data)[0]

            # Receive file content
            remaining = file_size
            file = open(output_path, "wb")

            while remaining > 0:
                chunk = conn.recv(min(BUFFER_SIZE, remaining))
                if not chunk:
                    break
                file.write(chunk)
                remaining -= len(chunk)

            file.close()

            # Send acknowledgement
            conn.sendall(b"ACK")

        except:
            # If error happens, just ignore and continue
            pass

        conn.close()


# =========================
# Client
# =========================
def run_client(server_ip, port, filepath):

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((server_ip, port))

        filename = os.path.basename(filepath)
        filename_bytes = filename.encode()

        # Send filename length
        client_socket.sendall(struct.pack("!I", len(filename_bytes)))

        # Send filename
        client_socket.sendall(filename_bytes)

        # Wait for server response
        response = client_socket.recv(2)

        if response == b"NO":
            print("Server rejected the file.")
            client_socket.close()
            sys.exit(1)

        # Send file size
        file_size = os.path.getsize(filepath)
        client_socket.sendall(struct.pack("!Q", file_size))

        # Send file content
        file = open(filepath, "rb")

        while True:
            chunk = file.read(BUFFER_SIZE)
            if not chunk:
                break
            client_socket.sendall(chunk)

        file.close()

        # Wait for ACK
        ack = client_socket.recv(3)

        if ack == b"ACK":
            print("File sent successfully.")
            sys.exit(0)
        else:
            sys.exit(255)

    except:
        sys.exit(255)


# =========================
# Main
# =========================
def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--server", action="store_true")
    parser.add_argument("--client", action="store_true")
    parser.add_argument("--connect", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9090)
    parser.add_argument("--outdir", default=".")
    parser.add_argument("--file")

    args = parser.parse_args()

    # Default mode is client
    if not args.server and not args.client:
        args.client = True

    if args.server:
        run_server(args.port, args.outdir)

    if args.client:
        if args.file is None:
            sys.exit(255)
        run_client(args.connect, args.port, args.file)


if __name__ == "__main__":
    main()
