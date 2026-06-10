# Shared PyInstaller excludes for Bridge-Robot-Utilities.
#
# None of these packages are used by any shipped utility. They only get pulled
# into the executables transitively (e.g. matplotlib's optional backends, or
# whatever else happens to be installed in the build Python). Excluding them
# keeps the executables small.
#
# endplay's only heavy *hard* dependency is matplotlib (which itself needs
# numpy / Pillow), because endplay/__init__.py eagerly does
# `from endplay.dealer import *`. matplotlib (and numpy, colorama) must stay.
EXCLUDES = [
    # Scientific / data libraries not used by the shipped tools
    'scipy',
    'pandas',
    # IPython / Jupyter stack
    'IPython',
    'ipykernel',
    'ipywidgets',
    'jupyter',
    'jupyter_client',
    'jupyter_core',
    'nbformat',
    'nbconvert',
    'notebook',
    'zmq',
    'tornado',
    # Editor / dev tooling
    'jedi',
    'parso',
    'pytest',
    '_pytest',
    'debugpy',
    # Async frameworks
    'gevent',
    'greenlet',
    # GUI toolkits matplotlib can optionally use (we only need the Agg backend)
    'PyQt5',
    'PyQt6',
    'PySide2',
    'PySide6',
    'wx',
    'gi',
    # Heavy ML libraries (only benchmark.py used these, and it is no longer shipped)
    'tensorflow',
    'torch',
]
