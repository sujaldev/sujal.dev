---
title: "A blog post about this blog itself."
date: "5 Aug, 2025"
last_modified: "12 Aug, 2025"
---

## Coming up with the design

I've been wanting to set up a blog for several years now, but I didn't want to use a cookie-cutter template. I wanted to
make a design from scratch that actually looked good to *me*. The problem is, I have no artistic talent for this kind of
thing. Show me a design and I can probably tell you what looks good and what does not (at least in my opinion), but
making one from scratch is, to say the least, *hard*.

So for the last two years, everytime I came across a website and thought "This looks super nice!", I'd note it down it
in a list. That list has become pretty long at this point, so I'll only mention the ones that I feel were the most
influential:
[Adam Blank](https://countablethoughts.com/),
[Notes on Data Structures and Programming Techniques](https://cs.yale.edu/homes/aspnes/classes/223/notes.html),
[Nota](https://nota-lang.org/),
[Daemonic Dispatches](https://www.daemonology.net/blog/),
[Urban Terror](https://www.urbanterror.info/home/),
[Gwern.net](https://gwern.net/),
[Satvik Saha](https://sahasatvik.github.io/),
[Tony Zorman](https://tony-zorman.com/).

Most of the people I've shown my website to so far, besides a few, don't seem to like the design as much as I do. But
I'm biased. In any case, I like it, so I'm going to keep it as it is for now.

## Reinventing the static site generator wheel for kicks

Since I was already doing the design from scratch, I figured I might as well do the static site generator from scratch
too. I didn't want to fight my setup in case whichever one I picked would not do things *exactly* how I wanted. And how
hard could a static site generator really be? Yeah, I keep falling for that one.

That said, I'm mostly done with the scripts I'm using to generate this site. It has most run-of-the-mill features you'd
expect from a static site generator, even some extras like a font subsetting script.

I'm using [Jinja2](https://github.com/pallets/jinja) as the templating engine and
[Mistletoe](https://github.com/miyuchina/mistletoe) as the Markdown parser combined with
[python-frontmatter](https://github.com/eyeseast/python-frontmatter) to parse, well, frontmatter. There were faster
alternatives to Mistletoe, but the article about standards compliance in their documentation won me over.

There's also a live mode where only the requested pages are built on the fly. I started with
[Flask](https://github.com/pallets/flask) for this but transitioned to [Quart](https://github.com/pallets/quart) later
for the native websocket support, which is required to auto-reload the page when
[watchfiles](https://github.com/samuelcolvin/watchfiles) or Quart's built-in reloader detects a change in the source
files.

If you want more details, you can dig through the [source repository](https://github.com/sujaldev/sujal.dev). I've
hardcoded some things here and there that I could have generalized but then what would be the point of writing my own
scripts in the first place.

## Do as I say, not as I do

Should've just used a cookie-cutter template with a prebuilt static site generator. Would've taken a lot less time.
But I'm proud of this.