---
title: "Creating a Window on Wayland from Scratch in Pure Python."
date: "21 Dec, 2025"
---

<p style="display: inline-block; padding: 20px; border: 2px solid red; border-radius: 5px;">
<b style="color: red">This post is still an unfinished draft.</b>
</p>

I wanted to see what kind of wizardry graphics toolkits like Qt or GTK perform when they create a window on a Wayland
desktop. It takes surprisingly little code to achieve the bare minimum goal of creating a window and drawing a static
image to it. In this article, I will walk through everything I learned about summoning a window on Wayland, using
nothing but Python's standard library.

::: aside
If you intend to do any _real_ work, you'll be much better off starting with
[libwayland](https://gitlab.freedesktop.org/wayland/wayland). It abstracts away many of the lower-level protocol details
that we'll be implementing from scratch here.
:::

The final code we'll end up writing by the end of this article is also available in its entirety
[here](https://github.com/sujaldev/sujal.dev/tree/main/content/posts/waygui/waygui.py).

## What does Wayland do?

I was confused about what role Wayland plays in the graphics stack. As an end user, all I ever had to do was use a
graphics toolkit and a window would appear. But what I hadn't considered was _other_ windows. Something must be
_compositing_ all the things visible on the screen (the panels, multiple windows, the desktop wallpaper, etc.) into a
single image that you can display on a monitor. This is the key role a Wayland _compositor_ fulfills on the desktop
among other important things (like handling input).

![Wayland Architecture](/static/images/wayland-6c705f19.svg "Wayland Architecture")

However, Wayland itself is not a compositor; it's the protocol that a conforming compositor and a client use to talk to
one another. But how do you talk to a Wayland compositor?

## Making a Connection to the Wayland Compositor

A client can use a Unix domain stream socket to communicate with a Wayland compositor. These are local sockets that
allow processes on the same host to talk to one another efficiently (they have another trick up their sleeve you'll see
later on). Let's start writing our first lines of code. We can use the socket module to create a Unix domain socket:

```python | linenos
import socket


def setup_socket():
    sock = socket.socket(family=socket.AF_UNIX, type=socket.SOCK_STREAM, proto=0)

    return sock
```

This creates the socket, but we haven't yet made a connection to the Wayland compositor. To find the path required to
connect to the compositor, we can do the following:

```python | linenos | highlight=[1, 2, (8, 13)]
import os
import socket


def setup_socket():
    sock = socket.socket(family=socket.AF_UNIX, type=socket.SOCK_STREAM, proto=0)

    name = os.getenv("WAYLAND_DISPLAY", default="wayland-0")
    if not name.startswith("/"):
        xdg_runtime_dir = os.getenv("XDG_RUNTIME_DIR", default=f"/run/user/{os.getuid()}")
        name = f"{xdg_runtime_dir}/{name}"

    sock.connect(name)

    return sock
```

First, we check if the `WAYLAND_DISPLAY` environment variable is set. If not, we'll assume a default value of
"wayland-0". Next, if the `WAYLAND_DISPLAY` variable is not an absolute path, we prepend the `XDG_RUNTIME_DIR`
environment variable to this value, with a default value set to "/run/user/\<user-id>". We have the path we need, so we
call `connect()` on the socket we created earlier.

We are now ready to talk to the compositor. We just need to figure out what to say.

## Learning How to Speak Wayland

Wayland is an object-oriented protocol. Every message we'll send or receive, to or from the server will be associated
to an object. Objects have an interface associated with them which is defined in
[wayland.xml](https://gitlab.freedesktop.org/wayland/wayland/-/blob/main/protocol/wayland.xml). This file can typically
be found inside `/usr/share/wayland` if you have the necessary package installed (wayland-devel on Fedora).

::: aside
I hadn't seen a protocol defined in this manner before, and I must say it's a neat trick.
:::

The interface for each object defines requests a client can invoke on the object, and events that the server can emit
for that object. Events need not be emitted in response to a request, for example if the user tries to resize your
window the server will spontaneously emit an event to let you know. Each request and event can also define arguments,
each with an associated type that we'll come back to later. This is what the corresponding XML looks like:

```xml

<protocol name="wayland">
    <interface name="some_object">
        <request name="some_request">
            <arg name="some_arg" type="some_primitive"/>
            ...
        </request>
        ...
        <event name="some_event">
            <arg name="some_arg" type="some_primitive"/>
            ...
        </event>
        ...
    </interface>
</protocol>
```

### Wire Format

Our conversation with the server will be about creating objects, invoking requests and receiving events associated with
a particular object, and eventually destroying that object. So we need a way to serialize this object talk into a byte
stream we can send over the socket we created earlier. Here's what that looks like:

![Wire Format](/static/images/wayland-wire-format-8cadff8c.svg "Wire Format")

The above depicts the structure of a _message_ in the wayland protocol. All fields in the message are aligned to 32-bit
words which are represented in the host's [byte order](https://en.wikipedia.org/wiki/Endianness). The first field in the
header is the object ID. It is a 32-bit unsigned integer that we assign to an object upon its creation. Both sides will
make a note of this mapping to allow identifying objects with a number.

The next field in the header is another 32-bit unsigned integer split into two 16-bit parts. The first part is the size
of the entire message (header + payload) in bytes. The second part is the opcode for either the request if the message
originates from the client, or the event if it originates from the server. The opcode is implicitly defined by the order
in which requests or events appear inside the object's interface in the XML file. The first request defined in an
interface corresponds to the opcode 0, the next to 1 and so on. Do note that requests and events are indexed separately.

::: aside
You might ask why not just treat `size` and `opcode` as two distinct 16-bit fields? On a little-endian host, the value
`0xAABBCCDD` should be represented as `0xDDCCBBAA`, but treating the two fields as separate, we'll get `0xBBAADDCC`
instead.
:::

Let's create a class to store the header:

```python | linenos | highlight=[(3, 10)]
import os
import socket
from dataclasses import dataclass


@dataclass
class Header:
    obj_id: int
    opcode: int
    size: int = 0


...
```

We should also add a way to serialize this header into bytes we can send on the wire:

```python | linenos | highlight=[3, 4, (14, 18)]
import os
import socket
import struct
import sys
from dataclasses import dataclass


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


...
```

The struct module helps convert our python types into a byte stream. If you're not sure what the "IHH" format means,
refer to the [documentation](https://docs.python.org/3/library/struct.html#byte-order-size-and-alignment) on the struct
module. We've had to separate the handling for each byte order because we're storing `size` and `opcode` separately,
which makes the `Header` class more convenient to work with, even though they are represented as a single 32-bit word on
the wire.

Next we'll add a method to instantiate the `Header` class from bytes received on the wire:

```python | linenos | highlight=[6, (13, 25)]
import os
import socket
import struct
import sys
from dataclasses import dataclass
from io import BytesIO


@dataclass
class Header:
    ...

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


...
```

We are reading 8 bytes (the size of a header) from the received data and parsing it into each field by passing the
expected byte stream format to the struct module. Again, we require separate handling for each byte order to split the
size and opcode fields. Next, we should store this `Header` in a new `Message` class that stores both the header and the
payload:

```python | linenos
...


@dataclass
class Message:
    header: Header
    payload: bytes

    def serialize(self):
        self.header.size = 8 + len(self.payload)
        return self.header.serialize() + self.payload


...
```

The payload consists of arguments for the particular request or event referenced in the header. Arguments are also
aligned to 32-bits, padding is added wherever required. We will