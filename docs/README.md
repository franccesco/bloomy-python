# Bloomy Python SDK Documentation

This directory contains the source files for the Bloomy Python SDK documentation, built with MkDocs.

## Local Development

To serve the documentation locally with auto-reload:

```bash
uv run mkdocs serve
```

Then visit http://127.0.0.1:8000/

## Building Documentation

To build the static documentation:

```bash
uv run mkdocs build
```

The built documentation will be in the `site/` directory.

## Deployment

Documentation is automatically deployed to GitHub Pages when changes are pushed to the main branch via GitHub Actions.

## Documentation Structure

- `index.md` - Home page
- `getting-started/` - Installation and setup guides
- `guide/` - User guides and tutorials
- `api/` - Auto-generated API reference using mkdocstrings

## Adding New Pages

1. Create a new `.md` file in the appropriate directory
2. Add the page to the navigation in `mkdocs.yml`
3. For API docs, use mkdocstrings directives to auto-generate from docstrings