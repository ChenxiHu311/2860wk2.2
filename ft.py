#!/usr/bin/env python3
import argparse
import os
import socket
import struct
import sys
from typing import Tuple

#############
# Constants #
#############
DEFAULT_PORT = 9090
DEFAULT_IPV4_ADDRESS = '127.0.0.1'
DEFAULT_IPV6_ADDRESS = '::1'
DEFAULT_OUTDIR = './'
BUFSIZE = 64 * 1024
MAX_FILENAME_LEN = 4096

LINE_OK = b'OK\n'
LINE_ERR = b'ERR\n'

###############
# I/O helpers #
###############

def recv_line(sock: socket.socket, max_len: int = MAX_FILENAME_LEN) -> bytes:
    data = bytearray()
    while True:
        ch = sock.recv(1)
        if not ch:
            raise ConnectionError("Connection closed")
        if ch == b'\n':
            break
        data += ch
        if len(data) > max_len:
            raise ValueError("Line too long")
    return bytes(data)

##########
# Server #
##########

def handle_client(conn: socket.socket, outdir: str) -> None:
    try:
        raw_line = recv_line(conn)

        try:
            filename = raw_line.decode('utf-8')
        except UnicodeDecodeError:
            conn.sendall(LINE_ERR)
            return

        filename = os.path.basename(filename)
        if filename == '':
            conn.sendall(LINE_ERR)
            return

        os.makedirs(outdir, exist_ok=True)
        dest_path = os.path.join(outdir, f"{filename}-received")

        if os.path.exists(dest_path):
            conn.sendall(LINE_ERR)
            return
        else:
            conn.sendall(LINE_OK)

        # Receive 8-byte file size
        hdr = b''
        while len(hdr) < 8:
            chunk = conn.recv(8 - len(hdr))
            if not chunk:
                raise ConnectionError("Size header incomplete")
            hdr += chunk

        (file_size,) = struct.unpack('!Q', hdr)

        remaining = file_size
        with open(dest_path, 'wb') as f:
            while remaining > 0:
                chunk = conn.recv(min(BUFSIZE, remaining))
                if not chunk:
                    raise ConnectionError("File data incomplete")
                f.write(chunk)
                remaining -= len(chunk)

        conn.sendall(LINE_OK)

    except Exception:
        try:
            conn.sendall(LINE_ERR)
        except Exception:
            pass


def run_server(port: int, outdir: str, ipv6: bool) -> None:
    family = socket.AF_INET6 if ipv6 else socket.AF_INET
    bind_addr = '::' if ipv6 else '0.0.0.0'

    with socket.socket(family, socket.SOCK_STREAM) as server:
        server.bind((bind_addr, port))
        server.listen()

        while True:
            conn, addr = server.accept()
            with conn:
                handle_client(conn, outdir)

##########
# Client #
##########

def run_client(server_ip: str, port: int, file_path: str, ipv6: bool) -> int:
    if not os.path.isfile(file_path):
        return 2

    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    family = socket.AF_INET6 if ipv6 else socket.AF_INET
    addr = (server_ip, port, 0, 0) if ipv6 else (server_ip, port)

    try:
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.connect(addr)

            # Send filename + newline
            sock.sendall(filename.encode('utf-8') + b'\n')

            # Wait for OK / ERR
            response = recv_line(sock)
            if response != b'OK':
                return 1

            # Send file size
            sock.sendall(struct.pack('!Q', file_size))

            # Send file content
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(BUFSIZE)
                    if not chunk:
                        break
                    sock.sendall(chunk)

            # Wait for final OK
            final = recv_line(sock)
            if final == b'OK':
                return 0
            else:
                return 255

    except Exception:
        return 255

################
# Main program #
################

def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description='TCP file transfer (client/server)')
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--server', action='store_true')
    mode.add_argument('--client', action='store_true')

    p.add_argument('--port', type=int, default=DEFAULT_PORT)
    p.add_argument('--outdir', default=DEFAULT_OUTDIR)
    p.add_argument('--connect', dest='server_ip', default=None)
    p.add_argument('--file', dest='file_path')
    p.add_argument('--ipv6', action='store_true')
    return p.parse_args(argv)

def main(argv=None) -> int:
    args = parse_args(argv)

    if args.server:
        run_server(args.port, args.outdir, ipv6=args.ipv6)
        return 0

    server_ip = args.server_ip
    if server_ip is None:
        server_ip = DEFAULT_IPV6_ADDRESS if args.ipv6 else DEFAULT_IPV4_ADDRESS

    if not args.file_path:
        return 2

    return run_client(server_ip, args.port, args.file_path, ipv6=args.ipv6)

if __name__ == '__main__':
    sys.exit(main())
