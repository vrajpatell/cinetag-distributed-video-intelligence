import subprocess
import sys
from pathlib import Path


def main() -> int:
    backend_root = Path(__file__).resolve().parents[1]
    alembic_ini = backend_root / "alembic.ini"
    return subprocess.call(
        ["alembic", "-c", str(alembic_ini), "upgrade", "head"],
        cwd=str(backend_root),
    )


if __name__ == '__main__':
    sys.exit(main())
