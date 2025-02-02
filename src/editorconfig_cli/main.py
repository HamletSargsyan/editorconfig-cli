import argparse
import re
import sys
from pathlib import Path

from tinylogging import Logger

logger = Logger("editorconfig-cli")
logger.formatter.template = "{level} | {message}"


def is_binary(file: Path) -> bool:
    try:
        with file.open("rb") as f:
            chunk = f.read(1024)
            if b"\0" in chunk:
                return True
    except Exception:
        return True
    return False


def is_ignored(
    file: Path,
    exclude: list[Path],
    use_gitignore: bool = True,
    gitignore_patterns: list[str] | None = None,
) -> bool:
    if not gitignore_patterns:
        gitignore_patterns = []

    if file in exclude:
        return True
    if use_gitignore:
        for pattern in gitignore_patterns:
            if file.match(pattern):
                return True
    return False


def get_gitignore_patterns(path: Path) -> list[str]:
    gitignore_file = path / ".gitignore"
    result = []
    if gitignore_file.exists():
        with gitignore_file.open() as f:
            result = [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
    else:
        logger.warning("No .gitignore file found at the specified path.")
    return result


def get_files(
    path: Path,
    exclude: list[Path] | None = None,
    use_gitignore: bool = False,
) -> list[Path]:
    if exclude is None:
        exclude = []
    result: list[Path] = []

    gitignore_patterns = []
    if use_gitignore:
        gitignore_patterns.extend(get_gitignore_patterns(path))

    for file in path.iterdir():
        if file.is_dir():
            if not is_ignored(file, exclude, use_gitignore, gitignore_patterns):
                result.extend(get_files(file, exclude, use_gitignore))
        else:
            if not is_ignored(
                file, exclude, use_gitignore, gitignore_patterns
            ) and not is_binary(file):
                result.append(file)
    return result


def parse_editorconfig(config_path: Path) -> dict[str, dict[str, str]]:
    with config_path.open() as file:
        content = file.readlines()

    config = {}
    current_section = None

    for line in content:
        line = line.strip()

        if not line or line.startswith((";", "/", "#")):
            continue

        if "root" in line:
            config["root"] = line.split("=")[1].strip()
        elif section_match := re.match(r"\[(.*)]", line):
            current_section = section_match.group(1)
            config[current_section] = {}
        elif "=" in line and current_section:
            key, value = map(str.strip, line.split("=", 1))
            config[current_section][key] = value

    return config


def format(file: Path, config: dict[str, dict[str, str]]):
    section = None
    for pattern, options in config.items():
        if pattern != "root" and file.match(pattern):
            section = options
            break

    if not section:
        return

    charset = section.get("charset", "utf-8")
    indent_style = section.get("indent_style", "space")
    indent_size = int(section.get("indent_size", 4))
    tab_width = int(section.get("tab_width", indent_size))
    end_of_line = section.get("end_of_line", "lf")
    trim_trailing_whitespace = (
        section.get("trim_trailing_whitespace", "false").lower() == "true"
    )
    insert_final_newline = (
        section.get("insert_final_newline", "false").lower() == "true"
    )
    try:
        with file.open("r", encoding=charset) as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        logger.warning(f"Unable to decode {file.name} with charset {charset}")
        return

    formatted_lines = []
    for line in lines:
        if trim_trailing_whitespace:
            line = line.rstrip()

        if indent_style == "space":
            line = line.replace("\t", " " * indent_size)
        elif indent_style == "tab":
            line = re.sub(r"^ +", lambda m: "\t" * (len(m.group(0)) // tab_width), line)

        formatted_lines.append(line)

    if insert_final_newline and (
        not formatted_lines or not formatted_lines[-1].endswith("\n")
    ):
        formatted_lines.append("\n")

    eol = {"lf": "\n", "cr": "\r", "crlf": "\r\n"}.get(end_of_line, "\n")
    formatted_content = eol.join(line.rstrip("\r\n") for line in formatted_lines)

    with file.open("w", encoding=charset) as f:
        f.write(formatted_content)


def find_main_config(paths: list[Path]) -> dict[str, dict[str, str]] | None:
    for path in paths:
        if path.name == ".editorconfig":
            config = parse_editorconfig(path)
            if config.get("root", False):
                return config
    return None


def main():
    parser = argparse.ArgumentParser(description="Format files based on .editorconfig")
    parser.add_argument("path", type=Path, help="Path to the directory to format")
    parser.add_argument(
        "--exclude",
        nargs="*",
        type=Path,
        default=[],
        help="Files or directories to exclude",
    )
    parser.add_argument(
        "--use-gitignore", action="store_true", help="Use .gitignore to exclude files"
    )
    args = parser.parse_args()

    path: Path = args.path
    exclude: list[Path] = args.exclude
    use_gitignore: bool = args.use_gitignore

    exclude.append(Path(".git"))

    files = get_files(path, exclude, use_gitignore=use_gitignore)
    config = find_main_config(files)

    if not config:
        logger.error("No .editorconfig file found")
        sys.exit(1)

    for file in files:
        if file.is_file():
            logger.info(f"Formatting file: {file}")
            format(file, config)


if __name__ == "__main__":
    main()
