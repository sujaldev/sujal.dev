# Fonts

This directory serves as the source for fonts, it is not directly used by the build script as subsetting is relatively
slow and the build script needs to be fast. Instead, `subset.py` is intended to be run once each time the font changes,
which I'm assuming is not going to be often, this will generate subsets of each font in the `/src/static/fonts`
directory from where it can be used as a regular asset in the build script.