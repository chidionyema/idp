"""Lint rules — AST visitors enforcing the four forcing functions.

Each module in this package exposes a `check_file(path)` returning
`list[tuple[int, str]]` and a `main(argv)` entrypoint.
"""
