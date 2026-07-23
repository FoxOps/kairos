#!/usr/bin/env python3
"""
Script to find duplicated code in the Kairos project.

Usage:
    python scripts/find_duplicates.py [directory] [min_lines]

Example:
    python scripts/find_duplicates.py app 5
"""

import ast
import hashlib
import os
import sys
from collections import defaultdict


def find_duplicate_functions(directory, min_lines=5):
    """
    Finds duplicated functions and methods in Python files.

    Args:
        directory: Directory to analyze
        min_lines: Minimum number of lines to consider a function

    Returns:
        Dict: {hash: [(filepath, function_name, start_line, end_line), ...]}
    """
    duplicates = defaultdict(list)

    for root, dirs, filenames in os.walk(directory):
        # Ignore special directories
        dirs[:] = [
            d
            for d in dirs
            if d not in [".git", "__pycache__", "venv", "instance", "migrations"]
        ]

        for filename in filenames:
            if filename.endswith(".py"):
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, encoding="utf-8") as f:
                        content = f.read()

                    # Parse with AST
                    tree = ast.parse(content)

                    # Extract functions and classes
                    for node in ast.walk(tree):
                        if isinstance(
                            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                        ):
                            # Get the function's source code
                            try:
                                start_line = node.lineno - 1
                                end_line = (
                                    node.end_lineno
                                    if hasattr(node, "end_lineno")
                                    else node.lineno
                                )

                                # Read the function's lines
                                lines = content.split("\n")
                                func_lines = lines[start_line:end_line]

                                # Filter out functions that are too short
                                if len(func_lines) >= min_lines:
                                    func_code = "\n".join(func_lines)
                                    # Normalize the code (strip comments, standardize whitespace)
                                    normalized = normalize_code(func_code)
                                    # Not a security use (code-similarity
                                    # fingerprint, not a cryptographic
                                    # hash) - usedforsecurity=False tells
                                    # both bandit and FIPS-mode Python
                                    # this is intentional.
                                    func_hash = hashlib.md5(
                                        normalized.encode(), usedforsecurity=False
                                    ).hexdigest()

                                    duplicates[func_hash].append(
                                        {
                                            "filepath": filepath,
                                            "name": node.name,
                                            "start_line": start_line + 1,
                                            "end_line": end_line,
                                            "type": type(node).__name__,
                                        }
                                    )
                            except Exception:
                                # Ignore parsing errors
                                pass
                except Exception as e:
                    print(
                        f"Erreur lors de l'analyse de {filepath}: {e}", file=sys.stderr
                    )

    # Filter to keep only duplicates
    return {k: v for k, v in duplicates.items() if len(v) > 1}


def normalize_code(code):
    """
    Normalizes code for better comparison.
    """
    # Strip comments
    lines = []
    for line in code.split("\n"):
        # Strip inline comments
        if "#" in line:
            line = line[: line.index("#")]
        lines.append(line.strip())

    # Standardize whitespace
    normalized = "\n".join(lines)
    # Collapse multiple spaces into one
    normalized = " ".join(normalized.split())

    return normalized


def find_duplicate_imports(directory):
    """
    Finds duplicated or unused imports.
    """
    import_counts = defaultdict(list)

    for root, dirs, filenames in os.walk(directory):
        dirs[:] = [
            d for d in dirs if d not in [".git", "__pycache__", "venv", "instance"]
        ]

        for filename in filenames:
            if filename.endswith(".py"):
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, encoding="utf-8") as f:
                        content = f.read()

                    tree = ast.parse(content)

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                import_name = alias.name
                                import_counts[import_name].append(filepath)
                        elif isinstance(node, ast.ImportFrom):
                            module = node.module
                            for alias in node.names:
                                import_name = (
                                    f"{module}.{alias.name}" if module else alias.name
                                )
                                import_counts[import_name].append(filepath)
                except Exception:
                    pass

    # Filter imports used in several files
    return {k: v for k, v in import_counts.items() if len(v) > 3}


def find_similar_code(directory, min_tokens=10):
    """
    Finds similar (not exactly duplicated) code using n-grams.
    """

    # Dictionary to store the n-grams
    ngrams = defaultdict(list)

    for root, dirs, filenames in os.walk(directory):
        dirs[:] = [
            d for d in dirs if d not in [".git", "__pycache__", "venv", "instance"]
        ]

        for filename in filenames:
            if filename.endswith(".py"):
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, encoding="utf-8") as f:
                        content = f.read()

                    # Extract tokens (keywords, identifiers)
                    tokens = extract_tokens(content)

                    # Build n-grams
                    for i in range(len(tokens) - min_tokens + 1):
                        ngram = tuple(tokens[i : i + min_tokens])
                        ngrams[ngram].append(filepath)
                except Exception:
                    pass

    # Filter n-grams that appear in several files
    return {k: v for k, v in ngrams.items() if len(set(v)) > 1}


def extract_tokens(code):
    """
    Extracts significant tokens from Python code.
    """
    import keyword
    import re

    # Python keywords
    python_keywords = set(keyword.kwlist)

    # Split the code into tokens
    tokens = re.findall(
        r"[a-zA-Z_][a-zA-Z0-9_]*|[+\-*/%=<>!&|^~:,;()\[\]{}]|\.|@|\\", code
    )

    # Filter significant tokens
    significant_tokens = []
    for token in tokens:
        if token.strip() and not token.isspace():
            # Keep keywords, identifiers and operators
            if (
                token in python_keywords
                or token.isidentifier()
                or token
                in "+-*/%=<>!&|^~:,;()[]{}@."  # noqa: S105 - Python tokenizer token, not a secret
            ):
                significant_tokens.append(token)

    return significant_tokens


def print_duplicates(duplicates):
    """
    Prints duplicates in a readable way.
    """
    if not duplicates:
        print("✅ Aucun code dupliqué détecté.")
        return

    print(f"⚠️  Trouvé {len(duplicates)} groupes de code dupliqué:\n")

    for i, (_hash_val, items) in enumerate(duplicates.items(), 1):
        print(f"{i}. {items[0]['name']} ({items[0]['type']})")
        print(f"   Taille: {items[0]['end_line'] - items[0]['start_line'] + 1} lignes")
        print("   Emplacements:")
        for item in items:
            print(f"     - {item['filepath']}:{item['start_line']}-{item['end_line']}")
        print()


def print_imports(imports):
    """
    Prints duplicated imports.
    """
    if not imports:
        print("✅ Aucun import dupliqué détecté.")
        return

    print("ℹ️  Imports utilisés dans plusieurs fichiers:\n")

    for import_name, files in sorted(imports.items()):
        print(f"  {import_name}: {len(files)} fichiers")
        for filepath in files[:5]:  # Show at most 5 files
            print(f"    - {filepath}")
        if len(files) > 5:
            print(f"    ... et {len(files) - 5} autres")
        print()


def main():
    """
    Main function.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Trouver le code dupliqué dans le projet Kairos"
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default="app",
        help="Répertoire à analyser (par défaut: app)",
    )
    parser.add_argument(
        "--min-lines",
        type=int,
        default=5,
        help="Nombre minimum de lignes pour considérer une fonction (par défaut: 5)",
    )
    parser.add_argument(
        "--check-imports",
        action="store_true",
        help="Vérifier aussi les imports dupliqués",
    )
    parser.add_argument(
        "--check-similar",
        action="store_true",
        help="Vérifier aussi le code similaire (lent)",
    )

    args = parser.parse_args()

    print("🔍 Recherche de code dupliqué dans Kairos")
    print("=" * 60)
    print()

    # Check the directory exists
    if not os.path.isdir(args.directory):
        print(
            f"❌ Erreur: Le répertoire '{args.directory}' n'existe pas.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"📁 Analyse du répertoire: {os.path.abspath(args.directory)}")
    print(f"📏 Taille minimum des fonctions: {args.min_lines} lignes")
    print()

    # Find duplicated functions
    print("🔎 Recherche de fonctions dupliquées...")
    duplicates = find_duplicate_functions(args.directory, args.min_lines)
    print_duplicates(duplicates)

    # Find duplicated imports
    if args.check_imports:
        print("🔎 Recherche d'imports dupliqués...")
        imports = find_duplicate_imports(args.directory)
        print_imports(imports)

    # Find similar code
    if args.check_similar:
        print("🔎 Recherche de code similaire (cela peut prendre du temps)...")
        similar = find_similar_code(args.directory)
        print(
            f"   Trouvé {len(similar)} séquences de code similaires dans plusieurs fichiers."
        )

    # Summary
    print("=" * 60)
    print("📊 Résumé:")
    print(f"   - Fonctions dupliquées: {len(duplicates)}")
    if args.check_imports:
        print(f"   - Imports dupliqués: {len(imports)}")
    if args.check_similar:
        print(f"   - Code similaire: {len(similar)}")
    print()

    # Return an exit code
    if duplicates:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
