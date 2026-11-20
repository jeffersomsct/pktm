"""Roda todos os testes (cada test_*.py e um script).   python tests/run_all.py"""
import subprocess
import sys
from pathlib import Path

failed = []
for test in sorted(Path(__file__).parent.glob("test_*.py")):
    result = subprocess.run([sys.executable, str(test)], capture_output=True, text=True)
    last_line = (result.stdout.strip().splitlines() or [""])[-1]
    if result.returncode == 0:
        print(f"ok     {test.name:32} {last_line}")
    else:
        failed.append(test.name)
        print(f"FALHA  {test.name}\n{result.stdout[-1500:]}{result.stderr[-1500:]}")
print(f"\n{'TUDO OK' if not failed else 'FALHARAM: ' + ', '.join(failed)}")
sys.exit(1 if failed else 0)
