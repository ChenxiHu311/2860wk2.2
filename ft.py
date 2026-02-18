#!/usr/bin/env python3

import socket
import argparse
import os
import struct
import sys

BUFFER_SIZE = 1024


# =========================
# Helper function to receive exact number of bytes
# =========================
def recv_all(sock, size):
    data = b""
    while len(data) < size:
        part = sock.recv(size - len(data))
        if not part:
            return None
        data += part
    return data


# =========================
# Server
# =========================
def run_server(port, outdir):

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("", port))
    server_socket.listen(1)

    while True:
        conn, addr = server_socket.accept()

        try:
            # Receive filename length (4 bytes)
            data = recv_all(conn, 4)
            if data is None:
                conn.close()
                continue

            name_length = struct.unpack("!I", data)[0]

            # Receive filename
            filename_bytes = recv_all(conn, name_length)
            if filename_bytes is None:
                conn.close()
                continue

            filename = filename_bytes.decode()
            output_path = os.path.join(outdir, filename + "-received")

            # Reject if file already exists
            if os.path.exists(output_path):
                conn.sendall(b"NO")
                conn.close()
                continue
            else:
                conn.sendall(b"OK")

            # Receive file size (8 bytes)
            size_data = recv_all(conn, 8)
            if size_data is None:
                conn.close()
                continue

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

            # Send ACK
            conn.sendall(b"ACK")

        except:
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

        # Wait for response
        response = recv_all(client_socket, 2)
        if response != b"OK":
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
        ack = recv_all(client_socket, 3)

        client_socket.close()

        if ack == b"ACK":
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
