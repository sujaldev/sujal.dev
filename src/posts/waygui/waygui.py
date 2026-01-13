import os
import socket
import struct
import sys
from dataclasses import dataclass
from io import BytesIO


@dataclass
class Header:
    obj_id: int
    opcode: int
    size: int = 0

    def serialize(self):
        size_and_opcode = (self.size << 16) | self.opcode
        return struct.pack("=II", self.obj_id, size_and_opcode)

    @staticmethod
    def frombytes(data: BytesIO) -> "Header | None":
        data = data.read(8)

        if len(data) != 8:
            return None

        obj_id, opcode_and_size = struct.unpack("=II", data)
        opcode = opcode_and_size & 0xFFFF
        size = opcode_and_size >> 16

        return Header(obj_id, opcode, size)


@dataclass
class Message:
    header: Header
    payload: bytes

    def serialize(self):
        self.header.size = 8 + len(self.payload)
        return self.header.serialize() + self.payload


def setup_socket():
    sock = socket.socket(family=socket.AF_UNIX, type=socket.SOCK_STREAM, proto=0)

    name = os.getenv("WAYLAND_DISPLAY", default="wayland-0")
    if not name.startswith("/"):
        xdg_runtime_dir = os.getenv("XDG_RUNTIME_DIR", default=f"/run/user/{os.getuid()}")
        name = f"{xdg_runtime_dir}/{name}"

    sock.connect(name)

    return sock


def main():
    pass


if __name__ == "__main__":
    main()
