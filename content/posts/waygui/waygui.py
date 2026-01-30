import os
import socket
import struct
from dataclasses import dataclass
from io import BytesIO


class WlPrimitive:
    @staticmethod
    def frombytes(data: BytesIO) -> "WlPrimitive":
        raise NotImplementedError

    def serialize(self) -> bytes:
        raise NotImplementedError


@dataclass
class UInt32(WlPrimitive):
    value: int

    @staticmethod
    def frombytes(data: BytesIO) -> "UInt32":
        return UInt32(struct.unpack("=I", data.read(4))[0])

    def serialize(self) -> bytes:
        return struct.pack("=I", self.value)


@dataclass
class Int32(WlPrimitive):
    value: int

    @staticmethod
    def frombytes(data: BytesIO) -> "Int32":
        return Int32(struct.unpack("=i", data.read(4))[0])

    def serialize(self) -> bytes:
        return struct.pack("=i", self.value)


class ObjID(UInt32):
    pass


class NewID(UInt32):
    pass


def padding(length: int) -> int:
    return (4 - (length % 4)) % 4


@dataclass
class String(WlPrimitive):
    value: str

    @staticmethod
    def frombytes(data: BytesIO) -> "String":
        length = UInt32.frombytes(data).value
        value = data.read(length - 1)
        data.read(1 + padding(length))
        return String(value.decode("utf8"))

    def serialize(self) -> bytes:
        value = bytes(self.value, "utf8")
        value += b"\0"  # Null Terminator

        size = len(value)
        value += b"\0" * padding(size)

        return UInt32(size).serialize() + value


@dataclass
class Array(WlPrimitive):
    value: bytes

    @staticmethod
    def frombytes(data: BytesIO) -> "WlPrimitive":
        size = UInt32.frombytes(data).value
        value = data.read(size)
        data.read(padding(size))
        return Array(value)

    def serialize(self) -> bytes:
        size = len(self.value)
        data = UInt32(size).serialize() + self.value
        data += b"\0" * padding(size)
        return data


@dataclass
class Fd(UInt32):
    value: int = 0

    def serialize(self) -> bytes:
        # The file descriptor is sent via ancillary data,
        # it does not serialize to actual bytes in the wire format.
        return b""


@dataclass
class Header:
    obj_id: ObjID
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
