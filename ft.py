#!/usr/bin/env python3

import socket
import argparse
import os
import struct
import sys

BUFFER_SIZE = 1024


def run_server(port, outdir):

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("", port))
    server_socket.listen(1)

    while True:
        conn, addr = server_socket.accept()

        try:
            data = conn.recv(4)
            if len(data) < 4:
                conn.close()
                continue

            name_length = struct.unpack("!I", data)[0]

            filename_bytes = conn.recv(name_length)
            filename = filename_bytes.decode()

            output_path = os.path.join(outdir, filename + "-received")

            if os.path.exists(output_path):
                conn.sendall(b"NO")
                conn.close()
                continue
            else:
                conn.sendall(b"OK")

            size_data = conn.recv(8)
            file_size = struct.unpack("!Q", size_data)[0]

            remaining = file_size
            file = open(output_path, "wb")

            while remaining > 0:
                chunk = conn.recv(min(BUFFER_SIZE, remaining))
                if not chunk:
                    break
                file.write(chunk)
                remaining -= len(chunk)

            file.close()

            conn.sendall(b"ACK")

        except:
            pass

        conn.close()


def run_client(server_ip, port, filepath):

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((server_ip, port))

        filename = os.path.basename(filepath)
        filename_bytes = filename.encode()

        client_socket.sendall(struct.pack("!I", len(filename_bytes)))
        client_socket.sendall(filename_bytes)

        response = client_socket.recv(2)

        if response == b"NO":
            client_socket.close()
            sys.exit(1)

        file_size = os.path.getsize(filepath)
        client_socket.sendall(struct.pack("!Q", file_size))

        file = open(filepath, "rb")

        while True:
            chunk = file.read(BUFFER_SIZE)
            if not chunk:
                break
            client_socket.sendall(chunk)

        file.close()

        ack = b""
        while len(ack) < 3:
            part = client_socket.recv(3 - len(ack))
            if not part:
                break
            ack += part

        if ack == b"ACK":
            sys.exit(0)
        else:
            sys.exit(255)

    except:
        sys.exit(255)


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
