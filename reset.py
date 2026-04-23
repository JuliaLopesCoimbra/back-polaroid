"""
Reset do estado local do robô Polaroid.
Apaga processed.json e os arquivos gerados em output/.

Uso:
    python reset.py
"""

import shutil
from pathlib import Path

BASE = Path(__file__).parent

# Suporta tanto o caminho novo (data/) quanto o legado (raiz do back/)
PROCESSED_CANDIDATES = [
    BASE / "data" / "processed.json",
    BASE / "processed.json",
]
OUTPUT_CANDIDATES = [
    BASE / "data" / "output",
    BASE / "output",
]


def remove_file(path: Path) -> None:
    if path.exists():
        path.unlink()
        print(f"  Apagado: {path}")
    else:
        print(f"  Não encontrado (ok): {path}")


def clear_directory(path: Path) -> None:
    if not path.exists():
        print(f"  Não encontrado (ok): {path}")
        return
    count = 0
    for f in path.iterdir():
        if f.is_file():
            f.unlink()
            count += 1
        elif f.is_dir():
            shutil.rmtree(f)
            count += 1
    print(f"  Limpo: {path}  ({count} item(s) removido(s))")


if __name__ == "__main__":
    print("\n=== Reset do Polaroid Robot ===\n")

    print("Apagando processed.json...")
    for p in PROCESSED_CANDIDATES:
        remove_file(p)

    print("\nLimpando output/...")
    for d in OUTPUT_CANDIDATES:
        clear_directory(d)

    print("\nReset completo. Rode python main.py para reprocessar.\n")
