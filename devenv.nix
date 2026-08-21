{ pkgs, ... }:
{
  packages = [
    pkgs.git
    pkgs.gnumake
    pkgs.pkg-config
    pkgs.python312
    pkgs.pkgsCross.arm-embedded.buildPackages.gcc
  ];

  env = {
    QMK_HOME = "$DEVENV_ROOT/src/vial-kb/vial-qmk";
    QMK_USERSPACE = "$DEVENV_ROOT";
  };

  enterShell = ''
    if [ ! -x "$DEVENV_ROOT/.venv/bin/python" ]; then
      python -m venv "$DEVENV_ROOT/.venv"
    fi

    export PATH="$DEVENV_ROOT/.venv/bin:$PATH"
    echo "Run qmk-bootstrap once to install the project-local QMK Python dependencies."
  '';

  scripts.qmk-bootstrap.exec = ''
    python -m pip install --upgrade pip
    python -m pip install -r "$DEVENV_ROOT/requirements-qmk.txt"
  '';
}
