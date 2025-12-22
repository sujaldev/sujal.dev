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
        if sys.byteorder == "little":
            return struct.pack("<IHH", self.obj_id, self.opcode, self.size)
        else:
            return struct.pack(">IHH", self.obj_id, self.size, self.opcode)

    @staticmethod
    def frombytes(data: BytesIO) -> "Header | None":
        data = data.read(8)

        if len(data) != 8:
            return None

        if sys.byteorder == "little":
            obj_id, opcode, size = struct.unpack("<IHH", data)
        else:
            obj_id, size, opcode = struct.unpack(">IHH", data)

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
