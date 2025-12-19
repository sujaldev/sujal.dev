---
title: "Creating a Window on Wayland from Scratch in Pure Python."
draft: true
---

Everyone seems to be talking about Wayland nowadays. Some people praise it like it will cure all cancer, while others
are convinced it's the work of the devil. I had little context to form an opinion, and figuring it out seemed like a fun
thing to do. So let's write a Wayland client using nothing but Python's standard library.

## What does Wayland do?

I was confused about what role Wayland plays in the graphics stack. As an end user, all I ever had to do was use a
graphics toolkit and a window would appear. But what I hadn't considered was _other_ windows. Something must be
_compositing_ all the things visible on the screen (the panels, multiple windows, the desktop wallpaper, etc.) into a
single image that you can display on a monitor. This is the key role a Wayland _compositor_ fulfills on the desktop
among other important things (like handling input).

![Wayland Architecture](/static/images/wayland.svg "Wayland Architecture")

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

```python | linenos | highlight=[1, (8, 12)]
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

Now that I knew Wayland is a protocol, I expected to find an RFC-style document I'd have to read and implement. However,
Wayland is defined using XML files that you can parse and even read like prose.

::: aside
I hadn't seen a protocol defined in this manner before, and I must say it's a neat trick.
:::

Wayland is an object-oriented protocol, everything we'll do will be associated to an object, which is made abundantly
clear by the protocol message format:

![Wire Format](/static/images/wayland-wire-format.svg "Wire Format")