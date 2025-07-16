# Include

Files in this directory are meant to be included inline in jinja templates using:

```jinja
{% include_raw("file_path") %}
```

The purpose for this is that these files are too small to warrant a separate request.