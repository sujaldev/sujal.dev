---
title: "A blog post about this blog itself."
date: "5 Aug, 2025"
last_modified: "18 Aug, 2025"
---

## Coming up with the design

I've been wanting to set up a blog for several years now, but I didn't want to use a cookie-cutter template. I wanted to
make a design from scratch that actually looked good to *me*. The problem is, I have no artistic talent for this kind of
thing. Show me a design and I can probably tell you what looks good and what does not (at least in my opinion), but
making one from scratch is, to say the least, *hard*.

So for the last two years, every time I came across a website and thought "This looks super nice!", I'd note it down it
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

### Markdown++

I've also added some additional syntax in my markdown posts.

#### Custom blocks

The following syntax can be used to add blocks of markdown with custom rendering:

```markdown
::: block_type | arg_1 | arg_2 | arg_n
contents
:::
```

Substituting `aside` in place of `block_type`, asides can be rendered as visible on the right, or below this paragraph
if you're viewing on a smaller screen size.

::: aside
Hey there! I'm an aside. I support _all_ the **usual** `markdown` features inside.
:::

The layout for asides is a bit wrong for now. It does not work for asides that are too close to one another, in which
case they'll overlap. Also, an aside that is too close to the bottom of the page might overflow to the footer. For now,
I'll just rely on myself as the author of the post to not reach those edge cases, because the fix I have in mind right
now will require javascript. Something I'm trying to avoid for layout at least.

#### Code fences with arguments

Line numbers can be enabled on code fences by passing the `linenos` argument to a code fence as below:

~~~markdown
```python | linenos
import foo
print("bar")
```
~~~

which will render as:

```python | linenos
import foo

print("bar")
```

And you can even highlight some lines with:

~~~markdown
```python | linenos | highlight=[101, (109, 111)]
class Vector:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def __add__(self, other: "Vector"):
        return Vector(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vector"):
        return Vector(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: int):
        return Vector(self.x * scalar, self.y * scalar)

    @property
    def xy(self):
        return self.x, self.y
```
~~~

Output:

```python | linenos | highlight=[101, (109, 111)]
class Vector:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def __add__(self, other: "Vector"):
        return Vector(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vector"):
        return Vector(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: int):
        return Vector(self.x * scalar, self.y * scalar)

    @property
    def xy(self):
        return self.x, self.y
```

Notice something peculiar about the numbers used in the highlight argument? Shouldn't `101` be `7` and the range
`(109, 111)` be `(15, 17)`? It should, but when you're authoring your post, you probably don't want to count relative to
where your code fence starts. A much more ergonomic solution is to use the absolute line numbering of your markdown
file, displayed by whatever editor you're using. And you can also turn this feature off by passing `relative_numbering`.

I intend to work on asciidoc style `` "`smart quotes"` `` next.

If you want more details, you can dig through the [source repository](https://github.com/sujaldev/sujal.dev). I've
hardcoded some things here and there that I could have generalized but then what would be the point of writing my own
scripts in the first place.

## Do as I say, not as I do

Should've just used a cookie-cutter template with a prebuilt static site generator. Would've taken a lot less time.
But having put in the work, I'm liking this setup so far.