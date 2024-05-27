"""Custom rez-bind file for Houdini."""

# Future
from __future__ import annotations

# Standard Library
import os
import pathlib
import re
from typing import TYPE_CHECKING, Optional

# Third Party
import rez.packages
from rez.package_maker import make_package
from rez.system import system
from rez.utils.lint_helper import defined, env, this
from rez.utils.platform_ import platform_

if TYPE_CHECKING:
    import argparse

    from rez.version._version import VersionRange


def get_houdini_version(hfs_path: pathlib.Path, only_major_minor: bool) -> str:
    """Determine the Houdini version string to be used with the package.

    Args:
        hfs_path: The $HFS path.
        only_major_minor: Whether to only use {major}.{minor} version number.

    Returns:
        The Houdini version string.
    """
    folder_name = hfs_path.name

    hfs_version = folder_name[3:]
    components = hfs_version.split(".")

    if len(components) > 2 and only_major_minor:
        components = components[:2]

    return ".".join(components)


def get_python_version(hfs_path: pathlib.Path) -> str:
    """Determine Houdini's Python {major}.{minor} version from $HFS/python/bin/python.

    Args:
        hfs_path: The $HFS path.

    Returns:
        The found python version.

    Raises:
        RuntimeError: If Houdini's Python version cannot be determined.
    """
    python_bin = hfs_path / "python" / "bin" / "python"

    python_bin = python_bin.resolve()

    result = re.match("python(\\d\\.\\d+)$", python_bin.name)

    if result is None:
        raise RuntimeError(f"Could not determine python version for {python_bin}")

    return result.group(1)


def get_tools(root: pathlib.Path) -> list[str]:
    """Build a list of tools that Houdini can provide.

    This will include executable files in $HB and $HSB which are not symlinks
    and do not contain '-bin' in their name.

    Args:
        root: The HFS path.

    Returns:
        A list of tool names.
    """
    bin_dir_names = ("bin", "houdini/sbin")

    found_tools = []

    for bin_dir_name in bin_dir_names:
        bin_path = root / bin_dir_name

        for child in bin_path.iterdir():
            if not child.is_file():
                continue

            if "-bin" in child.name:
                continue

            if child.is_symlink():
                continue

            if not os.access(child, os.X_OK):
                continue

            found_tools.append(child.name)

    return sorted(found_tools)


def setup_parser(parser: argparse.ArgumentParser) -> None:
    """Set up the argument parser for Houdini install related items.

    Args:
        parser: The program argument parser.
    """
    parser.add_argument(
        "hfs", type=str, metavar="PATH", help="bind other houdini version than default"
    )

    parser.add_argument(
        "--major-minor-only",
        action="store_true",
        help="Only use major.minor version number",
    )


def commands() -> None:
    """Configure the environment."""
    # We need to add Houdini related bin directories to the front of the path.
    env.PATH.prepend("$HSB")
    env.PATH.prepend("$HB")


def pre_commands() -> None:
    """Configure the environment before primary configuration.

    This function will set most of the Houdini related environment variables, similar
    to the 'houdini_setup' commands on linux.
    """
    # Export the Python version using the soft requirement for our package.
    for r in this.requires:
        if r.name == "python":
            env.HOUDINI_PYTHON_VERSION = str(r.range.split()[0])[1:]
            break

    else:
        raise RuntimeError(f"Could not determine Python version for {this}")

    env.HOUDINI_MAJOR_RELEASE = "${REZ_HOUDINI_MAJOR_VERSION}"
    env.HOUDINI_MINOR_RELEASE = "${REZ_HOUDINI_MINOR_VERSION}"
    env.HOUDINI_BUILD_VERSION = "${REZ_HOUDINI_PATCH_VERSION}"

    env.HOUDINI_VERSION = (
        "${HOUDINI_MAJOR_RELEASE}.${HOUDINI_MINOR_RELEASE}.${HOUDINI_BUILD_VERSION}"
    )

    env.HFS = "{root}/ext"

    # Handy shortcuts
    env.H = "${HFS}"
    env.HB = "${H}/bin"
    env.HDSO = "${H}/dsolib"
    env.HH = "${H}/houdini"
    env.HHC = "${HH}/config"
    env.HHP = "${HH}/python${HOUDINI_PYTHON_VERSION}libs"
    env.HT = "${H}/toolkit"
    env.HSB = "${HH}/sbin"

    env.TEMP = "/tmp"

    env.LD_LIBRARY_PATH.prepend("$HDSO")

    env.HIH = "${HOME}/houdini${HOUDINI_MAJOR_RELEASE}.${HOUDINI_MINOR_RELEASE}"
    env.HIS = "${HH}"

    env.CMAKE_PREFIX_PATH.append("${HT}/cmake")


def post_commands() -> None:
    """Configure the environment after the main configuration has been run.

    The primary function happening here is an attempt to fix any potential bad
    setup of the core HOUDINI*_PATH variables. If any packages set these paths, the
    $HFS equivalents must be present otherwise Houdini can fail to startup.

    If any of the following variables are defined then we'll append '&' to the end of
    them to ensure Houdini has its default paths included:
        - HOUDINI_PATH
        - HOUDINI_DSO_PATH
        - HOUDINI_OTLSCAN_PATH
        - HOUDINI_SCRIPT_PATH
        - HOUDINI_TOOLBAR_PATH
    """
    special_paths = [
        "HOUDINI_PATH",
        "HOUDINI_DSO_PATH",
        "HOUDINI_OTLSCAN_PATH",
        "HOUDINI_SCRIPT_PATH",
        "HOUDINI_TOOLBAR_PATH",
    ]

    for special_path in special_paths:
        if defined(special_path):
            path_obj = getattr(env, special_path)

            if "&" not in path_obj.value():
                path_obj.append("&")


def bind(
    path: str,
    version_range: Optional[VersionRange] = None,
    opts: Optional[argparse.Namespace] = None,
    parser: Optional[argparse.ArgumentParser] = None,
) -> list[rez.packages.Variant]:
    """Create a new Houdini package version."""
    hfs_path = pathlib.Path(opts.hfs)
    only_major_minor = opts.major_minor_only

    version = get_houdini_version(hfs_path, only_major_minor)

    def make_root(variant, root):
        link_path = os.path.join(root, "ext")
        platform_.symlink(hfs_path, link_path)

    requires = [
        f"~python-{get_python_version(hfs_path)}",
    ]

    with make_package("houdinier", path, make_root=make_root) as pkg:
        pkg.version = version
        pkg.tools = get_tools(hfs_path)
        pkg.commands = commands
        pkg.variants = [system.variant]
        pkg.pre_commands = pre_commands
        pkg.post_commands = post_commands
        pkg.has_plugins = True
        pkg.description = "Base Houdini package"

        pkg.requires = requires

    return pkg.installed_variants
