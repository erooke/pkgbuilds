#! /usr/bin/env python
import os
import sys
from pathlib import Path
from subprocess import PIPE, CalledProcessError, check_call, run

build_dir = Path.home() / ".local" / "pkgs"
repo = build_dir / "custom.db.tar.zst"


def build_pkg(directory):
    print(f"Building {directory}")
    cwd = Path.cwd()
    try:
        os.chdir(directory)

        # Update the version
        check_call(["makepkg", "--nobuild"])

        proc = run(
            ["makepkg", "--packagelist"],
            encoding="utf-8",
            stdout=PIPE,
            check=True,
        )

        for package in map(Path, proc.stdout.split()):
            dest = build_dir / package.name

            if not dest.exists():
                # We need to build this package
                break

            if package.exists():
                # This already exists, no reason to copy it back here
                continue

            package.hardlink_to(dest)
        else:
            # There is nothing to build
            return

        run(
            ["makepkg", "-s", "--noconfirm", "-r"],
            stderr=PIPE,
            check=True,
            encoding="utf-8",
        )

    except CalledProcessError as e:
        if "A package has already been built" not in e.stderr:
            print(e.stderr)
            raise e

        print(f"{directory} has already been built")

    finally:
        os.chdir(cwd)


def install_pkg(directory: Path):
    cwd = Path.cwd()
    try:
        os.chdir(directory)
        for package in directory.glob("*.zst"):
            dest = build_dir / package.name
            if dest.exists():
                dest.unlink()

            dest.hardlink_to(package)
            # check_call(["repo-add", str(repo), package])
    finally:
        os.chdir(cwd)


def sync_pkgs():
    packages = list(build_dir.glob("*.pkg.tar.zst"))
    check_call(["repo-add", str(repo)] + packages)
    check_call(["rsync", "-Pa", build_dir, "roo.ke:pkgs"])


def download_aur():
    packages = Path("aur").read_text(encoding="utf-8").split()
    git_ignore(packages)
    check_call(["yay", "-Gf"] + packages)


def git_ignore(packages):
    content = ["*.zip", "src/", "*.zst", "pkg/", "\n# AUR packages\n"] + list(packages)

    (Path.cwd() / ".gitignore").write_text("\n".join(content), encoding="utf-8")


def main():
    build_dir.mkdir(exist_ok=True, parents=True)
    print("Downloading aur packages")
    download_aur()
    for p in Path.cwd().iterdir():
        if not p.is_dir():
            continue

        if p.name == ".git":
            continue

        if p.name == "library":
            continue

        build_pkg(p)
        install_pkg(p)

    sync_pkgs()

    return 0


if __name__ == "__main__":
    sys.exit(main())
