# Environment setup for Troostwatch

This project targets Python 3.14+. The repo includes helper scripts to install Python and create a virtual environment on Windows.

Windows (PowerShell):

- Install Python 3.14 (system-wide) using the provided installer script:

```powershell
# Downloads and runs the official Python 3.14 installer
./install-python314.ps1
```

- Create and activate the virtual environment, then install dependencies:

```powershell
# Create venv and install requirements
./setup-env.ps1
# Or manually:
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .[dev]
```

Notes:
- After running the system installer, you may need to restart your shell for `python` to point to the new installation.
- The `setup-env.ps1` script activates the venv and installs `requirements.txt`.
- CI runs and tests target Python 3.14; please use a Python 3.14 interpreter for development to avoid incompatibilities.
