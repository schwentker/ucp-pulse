import socket

def blocked(*args, **kwargs):
    raise RuntimeError("network disabled in test subprocess")

socket.socket.connect = blocked
socket.socket.connect_ex = blocked
socket.create_connection = blocked
socket.getaddrinfo = blocked
