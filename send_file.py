# I used some code from this source
# https://www.thepythoncode.com/article/send-receive-files-using-sockets-python
# and from DS lab sample as well

import socket
import os
import sys
from time import sleep
import tqdm

BUFFER_SIZE = 4096


def main(argv):
    filename = argv[0]
    host = argv[1]
    port = int(argv[2])

    try:
        filesize = os.path.getsize(filename)

    except OSError:
        print("File '%s' does not exists or is inaccessible" % filename)
        sys.exit()

    sock = socket.socket()
    print("Connecting to server...")
    sock.connect((host, port))
    print("Connected to server, started file sending...")
    sock.send(f"{filename}".encode())
    sleep(1)
    with open(filename, "rb") as f:
        progress = tqdm.tqdm(range(filesize), "Progress",
                             unit="B", unit_scale=True, unit_divisor=1024)
        while True:
            bytes_read = f.read(BUFFER_SIZE)
            if not bytes_read:
                break
            sock.sendall(bytes_read)
            progress.update(len(bytes_read))
    sock.close()


if __name__ == "__main__":
    main(sys.argv[1:])
