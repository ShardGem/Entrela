# Recursos, metadados científicos e extensões nativas fazem parte do pacote.
from pathlib import Path
import runpy

from PyInstaller.compat import is_win
from PyInstaller.utils.hooks import collect_all, collect_data_files, copy_metadata

root = Path(SPECPATH).parent
app_version = runpy.run_path(str(root / 'core' / '__init__.py'))['__version__']
datas = collect_data_files('gui', includes=['assets/**'])
binaries, hiddenimports = [], [
    'matplotlib.backends.backend_pdf', 'matplotlib.backends.backend_svg',
    'matplotlib.backends.backend_agg', 'mpl_toolkits.mplot3d',
]
for package in ('qiskit', 'qiskit_aer', 'pylatexenc'):
    package_data, package_binaries, package_imports = collect_all(package, include_py_files=False)
    datas += package_data
    binaries += package_binaries
    hiddenimports += package_imports
if is_win:
    from PyInstaller.utils.hooks import collect_delvewheel_libs_directory
    datas, binaries = collect_delvewheel_libs_directory('qiskit_aer', datas=datas, binaries=binaries)
for distribution in ('entrela', 'qiskit', 'qiskit-aer', 'numpy', 'scipy', 'PySide6', 'matplotlib', 'Pillow'):
    datas += copy_metadata(distribution)

version_resource = None
if is_win:
    from PyInstaller.utils.win32.versioninfo import (
        VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct,
    )
    numbers = tuple(int(part) for part in app_version.split('.')) + (0,)
    version_resource = VSVersionInfo(
        ffi=FixedFileInfo(filevers=numbers, prodvers=numbers, mask=0x3f,
                          flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
        kids=[StringFileInfo([StringTable('041604B0', [
            StringStruct('FileDescription', 'Entrela · laboratório quântico'),
            StringStruct('FileVersion', app_version), StringStruct('ProductName', 'Entrela'),
            StringStruct('ProductVersion', app_version), StringStruct('OriginalFilename', 'Entrela.exe'),
        ])]), VarFileInfo([VarStruct('Translation', [1046, 1200])])],
    )

analysis = Analysis(
    [str(root / 'packaging' / 'launcher.py')], pathex=[str(root)],
    binaries=binaries, datas=datas, hiddenimports=hiddenimports,
    excludes=['PyQt5', 'PyQt6', 'PySide2', 'pytest'],
    hooksconfig={'matplotlib': {'backends': ['QtAgg', 'Agg']}},
)
archive = PYZ(analysis.pure)
executable = EXE(
    archive, analysis.scripts, [], exclude_binaries=True, name='Entrela',
    console=False, upx=False, version=version_resource,
    icon=str(root / 'gui' / 'assets' / 'icons' / 'entrela.ico') if is_win else None,
)
collection = COLLECT(executable, analysis.binaries, analysis.datas, name='Entrela', upx=False)
