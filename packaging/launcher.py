"""Entrada do executável; a verificação usa somente armazenamento temporário."""
import os
from pathlib import Path
import sys

if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--verificar-pacote':
        diagnostic_path = Path(sys.argv[2]).resolve()
        diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
        diagnostic_log = diagnostic_path.with_suffix('.log').open('w', encoding='utf-8', buffering=1)
        sys.stdout = sys.stderr = diagnostic_log
        from PySide6.QtCore import qInstallMessageHandler
        qInstallMessageHandler(lambda _kind, _context, message: diagnostic_log.write(message + '\n'))
        from gui.bundle_check import check_bundle
        raise SystemExit(check_bundle(Path(sys.argv[2])))
    from gui.application import main
    raise SystemExit(main())
