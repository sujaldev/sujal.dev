import re
from datetime import datetime
from string import ascii_lowercase, digits

from ssg.constants import *


def create_post():
    while True:
        title = input("Enter post title: ")
        if title:
            break
        else:
            print("Title cannot be empty!")

    slug_whitelist = ascii_lowercase + digits + "-" + " "
    slug = ''.join([
        char for char in title.lower()
        if char in slug_whitelist
    ])
    slug = re.sub(r"\s+", "-", slug)
    print(f"\nExtracted slug: {slug}")
    override_slug = input("Enter slug (or leave empty to use above): ")

    while True:
        today = datetime.today()
        # A format code for day of the month without zero padding doesn't seem to be documented.
        # I did find however that '%-d' works, but I'll err on the side of caution.
        date = today.strftime(str(today.day) + " %b, %Y")
        date = input(f"\nEnter date (or leave empty to use '{date}'): ") or date

        try:
            datetime.strptime(date, "%d %b, %Y")
            break
        except ValueError:
            print("Incorrect date format. Expected format: '4 Aug, 2025'.")

    while True:
        is_draft = input("\nShould this post be marked as a draft? (Y/n):").lower() or "y"

        if is_draft in ("y", "n"):
            is_draft = is_draft == "y"
            break

        print("Enter 'y' for yes or 'n' for no.")

    frontmatter = {
        "title": f'"{title}"',
        "date": f'"{date}"',
    }

    if override_slug:
        frontmatter["slug"] = f'"{override_slug}"'

    if is_draft:
        frontmatter["draft"] = "true"

    frontmatter = "---\n" + "\n".join([f"{key}: {val}" for key, val in frontmatter.items()]) + "\n---\n"

    last_post = sorted((CONTENT_DIR / "posts").rglob("*.md"))
    last_post = last_post[-1].name if last_post else "00-"

    new_post_number = int(last_post.split("-")[0]) + 1
    new_post_number = f"{new_post_number:0>2}"

    new_post_path = CONTENT_DIR / f"posts/{new_post_number}-{override_slug or slug}.md"
    new_post_path.parent.mkdir(parents=True, exist_ok=True)

    with open(new_post_path, "w") as file:
        file.write(frontmatter)
