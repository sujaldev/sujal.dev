---
title: "Fixing SSH Access to an Oracle VPS Without Reprovisioning"
draft: true
---

## Discovering I'm locked out

It's a bright Friday morning. You've just woken up, refreshed and ready to tackle the day. You turn on your computer,
open a terminal, and start typing in the same trusty command you've always used to ssh into your VPS, only to be met
with:

```bash
$ ssh user@myvps
user@myvps: Permission denied (publickey).
```

You're left pulling your hair, wondering why your VPS won't talk to you anymore. Worry not, I've got just the solution
to make amends.

## What went wrong?