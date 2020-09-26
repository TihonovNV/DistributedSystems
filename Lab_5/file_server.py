# I used some code from this source
# https://www.thepythoncode.com/article/send-receive-files-using-sockets-python
# and from DS lab sample as well

import socket
import os
from threading import Thread

BUFFER_SIZE = 4096


class ClientListener(Thread):
    def __init__(self, name: str, sock: socket.socket):
        super().__init__(daemon=True)
        self.sock = sock
        self.name = name

    def run(self):
        filename = self.sock.recv(BUFFER_SIZE).decode()
        dot = filename.find('.')
        extension = '' if dot == -1 else filename[dot + 1:]
        name = filename if dot == -1 else filename[:dot]
        if(os.path.isfile(filename)):
            i = 1
            while True:
                if (os.path.isfile(name + "_copy" + str(i) + '.' + extension)):
                    i += 1
                else:
                    filename = name + "_copy" + str(i) + '.' + extension
                    break
        with open(filename, "wb") as f:
            while True:
                data = self.sock.recv(BUFFER_SIZE)
                if not data:
                    break
                f.write(data)
        print("File received succesfully")
        self.sock.close()


def main():
    next_name = 1

    s = socket.socket()
    s.bind(('', 8800))
    s.listen()
    while True:
        con, addr = s.accept()
        name = 'user_' + str(next_name)
        next_name += 1
        print(str(addr) + ' connected as ' + name)
        ClientListener(name, con).start()


if __name__ == "__main__":
    main()
