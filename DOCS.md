# Documentation Development

This project uses [MkDocs](https://www.mkdocs.org/) with the [Material theme](https://squidfunk.github.io/mkdocs-material/) for documentation.

## Setup

Install MkDocs as a uv tool (only needs to be done once):

```bash
uv tool install mkdocs --with mkdocs-material --with pymdown-extensions
```

## Development

Start the development server to preview docs locally:

```bash
uv tool run mkdocs serve
```

Then open http://127.0.0.1:8000/censo-argentino-qgis/ in your browser.

The server will automatically reload when you edit documentation files.

## Building

Build the static site:

```bash
uv tool run mkdocs build
```

This generates the site in the `site/` directory.

## Deployment

The documentation is automatically deployed to GitHub Pages when changes are pushed to the `main` branch.

To manually deploy:

```bash
uv tool run mkdocs gh-deploy
```

## Structure

- `docs/` - Documentation source files (Markdown)
- `mkdocs.yml` - Configuration file
- `site/` - Generated static site (ignored by git)

## Documentation Files

- `index.md` - Homepage
- `instalacion.md` - Installation guide
- `inicio-rapido.md` - Quick start guide
- `guia-usuario.md` - User guide
- `sql.md` - SQL query mode documentation
- `examples/basico.md` - Basic examples
- `solucion-problemas.md` - Troubleshooting
- `contribuir.md` - Contributing guide
- `CHANGELOG.md` - Version history
