"""CLI assembler for UVM (Variant 13) - Stage 2."""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

try:
    import yaml
except ModuleNotFoundError:
    yaml = None

OPCODE_LOAD_CONST = 111
OPCODE_READ_MEM = 17
OPCODE_WRITE_MEM = 46
OPCODE_UNARY_MINUS = 87

INSTRUCTION_SIZE_BYTES = 13
FIELD_B_SHIFT = 7
FIELD_C_SHIFT = 35

MIN_FIELD_VALUE = 0
ADDR_BITS = 28
CONST_BITS = 14
MAX_ADDR_VALUE = (1 << ADDR_BITS) - 1
MAX_CONST_VALUE = (1 << CONST_BITS) - 1

FIRST_CMD_INDEX = 1
FIRST_INDEX = 0
LAST_INDEX = -1
SPLIT_ONCE = 1
INT_AUTO_BASE = 0
COMMENT_CHAR = "#"
ROOT_KEY = "program"
ROOT_KEY_HEADER = "program:"
LIST_PREFIX = "-"
LIST_PREFIX_LEN = 1
YAML_ERROR = yaml.YAMLError if yaml is not None else ValueError


@dataclass(frozen=True)
class CommandSpec:
    """Specification mapping YAML keys to UVM instruction fields."""

    opcode: int
    field_b_key: str
    field_c_key: str
    max_b: int
    max_c: int


@dataclass(frozen=True)
class Instruction:
    """Internal representation of a single UVM instruction."""

    field_a: int
    field_b: int
    field_c: int

    def format_fields(self) -> str:
        """Format fields as shown in UVM specification tests."""
        return (
            f"A={self.field_a}, "
            f"B={self.field_b}, "
            f"C={self.field_c}"
        )


COMMAND_SPECS = {
    "load_const": CommandSpec(
        opcode=OPCODE_LOAD_CONST,
        field_b_key="dest",
        field_c_key="value",
        max_b=MAX_ADDR_VALUE,
        max_c=MAX_CONST_VALUE,
    ),
    "read_mem": CommandSpec(
        opcode=OPCODE_READ_MEM,
        field_b_key="dest",
        field_c_key="src",
        max_b=MAX_ADDR_VALUE,
        max_c=MAX_ADDR_VALUE,
    ),
    "write_mem": CommandSpec(
        opcode=OPCODE_WRITE_MEM,
        field_b_key="src",
        field_c_key="dest",
        max_b=MAX_ADDR_VALUE,
        max_c=MAX_ADDR_VALUE,
    ),
    "unary_minus": CommandSpec(
        opcode=OPCODE_UNARY_MINUS,
        field_b_key="src_ptr",
        field_c_key="dest",
        max_b=MAX_ADDR_VALUE,
        max_c=MAX_ADDR_VALUE,
    ),
}


def parse_scalar(raw_value: str) -> Any:
    """Convert a YAML scalar string into int or str."""
    text = raw_value.strip()
    try:
        return int(text, INT_AUTO_BASE)
    except ValueError:
        return text.strip("\"'")


def parse_key_value(line: str) -> tuple[str, Any]:
    """Split a 'key: value' YAML line into key and parsed value."""
    if ":" not in line:
        raise ValueError(f"Некорректная строка YAML: {line}")
    key, raw_value = line.split(":", SPLIT_ONCE)
    return key.strip(), parse_scalar(raw_value)


def append_yaml_line(items: list[dict[str, Any]], line: str) -> None:
    """Add a YAML list entry or key-value pair to the items list."""
    if line.startswith(LIST_PREFIX):
        items.append({})
        line = line[LIST_PREFIX_LEN:].strip()
    if not line:
        return
    if not items:
        raise ValueError("Команды в 'program' должны быть списком.")
    key, value = parse_key_value(line)
    items[LAST_INDEX][key] = value


def parse_simple_yaml(source_text: str) -> dict[str, Any]:
    """Parse the UVM YAML subset without external dependencies."""
    items: list[dict[str, Any]] = []
    found_program = False
    for raw_line in source_text.splitlines():
        line = raw_line.split(COMMENT_CHAR, SPLIT_ONCE)[FIRST_INDEX]
        line = line.strip()
        if not line:
            continue
        if line == ROOT_KEY_HEADER:
            found_program = True
            continue
        if not found_program:
            raise ValueError("Ожидался корневой ключ 'program:'.")
        append_yaml_line(items, line)
    return {ROOT_KEY: items} if found_program else {}


def load_yaml_data(source_text: str) -> Any:
    """Load YAML via PyYAML if installed, else built-in parser."""
    if yaml is not None:
        return yaml.safe_load(source_text)
    return parse_simple_yaml(source_text)


def validate_field(
    value: Any,
    field_name: str,
    max_value: int,
    index: int,
) -> int:
    """Validate that an operand is an integer within allowed bounds."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"Команда #{index}: поле '{field_name}' "
            f"должно быть целым числом."
        )
    if value < MIN_FIELD_VALUE or value > max_value:
        raise ValueError(
            f"Команда #{index}: поле '{field_name}'={value} "
            f"вне диапазона [{MIN_FIELD_VALUE}, {max_value}]."
        )
    return value


def extract_operand(
    raw_item: dict[str, Any],
    key: str,
    max_value: int,
    index: int,
) -> int:
    """Extract and validate a required integer operand."""
    if key not in raw_item:
        raise ValueError(
            f"Команда #{index}: отсутствует поле '{key}'."
        )
    return validate_field(raw_item[key], key, max_value, index)


def parse_instruction(raw_item: Any, index: int) -> Instruction:
    """Convert a single YAML mapping into an IR instruction."""
    if not isinstance(raw_item, dict):
        raise ValueError(
            f"Команда #{index} должна быть YAML-объектом."
        )
    op_name = raw_item.get("op")
    if op_name not in COMMAND_SPECS:
        raise ValueError(
            f"Команда #{index}: неизвестная операция '{op_name}'."
        )
    spec = COMMAND_SPECS[op_name]
    allowed_keys = {"op", spec.field_b_key, spec.field_c_key}
    extra_keys = set(raw_item.keys()) - allowed_keys
    if extra_keys:
        raise ValueError(
            f"Команда #{index}: лишние поля {sorted(extra_keys)}."
        )
    field_b = extract_operand(
        raw_item, spec.field_b_key, spec.max_b, index
    )
    field_c = extract_operand(
        raw_item, spec.field_c_key, spec.max_c, index
    )
    return Instruction(
        field_a=spec.opcode,
        field_b=field_b,
        field_c=field_c,
    )


def translate_yaml(source_text: str) -> list[Instruction]:
    """Parse YAML assembly text into a list of IR instructions."""
    data = load_yaml_data(source_text)
    if not isinstance(data, dict) or ROOT_KEY not in data:
        raise ValueError(
            "YAML-файл должен содержать корневой ключ 'program'."
        )
    raw_program = data[ROOT_KEY]
    if not isinstance(raw_program, list):
        raise ValueError(
            "Значение ключа 'program' должно быть списком команд."
        )
    return [
        parse_instruction(item, idx)
        for idx, item in enumerate(raw_program, start=FIRST_CMD_INDEX)
    ]


def encode_instruction(instr: Instruction) -> bytes:
    """Encode a single IR instruction into 13-byte machine code."""
    packed = (
        instr.field_a
        | (instr.field_b << FIELD_B_SHIFT)
        | (instr.field_c << FIELD_C_SHIFT)
    )
    return packed.to_bytes(INSTRUCTION_SIZE_BYTES, byteorder="little")


def encode_program(instructions: list[Instruction]) -> bytes:
    """Translate a list of IR instructions into machine code bytes."""
    return b"".join(
        encode_instruction(instr) for instr in instructions
    )


def format_bytes(raw_bytes: bytes) -> str:
    """Format bytes as comma-separated hex values."""
    return ", ".join(f"0x{byte:02X}" for byte in raw_bytes)


def write_binary(output_path: Path, binary_data: bytes) -> None:
    """Write assembled machine code to the output binary file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(binary_data)


def build_arg_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser for the assembler."""
    parser = argparse.ArgumentParser(
        description="Ассемблер УВМ (вариант 13)."
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="Путь к исходному YAML-файлу с программой.",
    )
    parser.add_argument(
        "output_path",
        type=Path,
        help="Путь к двоичному файлу-результату.",
    )
    parser.add_argument(
        "-t",
        "--test",
        action="store_true",
        help="Включить режим тестирования (вывод байтов).",
    )
    return parser


def main() -> None:
    """Entry point for the assembler CLI application."""
    parser = build_arg_parser()
    args = parser.parse_args()
    try:
        source_text = args.input_path.read_text(encoding="utf-8")
        instructions = translate_yaml(source_text)
        binary_data = encode_program(instructions)
        write_binary(args.output_path, binary_data)
    except (OSError, ValueError, YAML_ERROR) as exc:
        sys.exit(f"Ошибка: {exc}")
    print(f"Размер двоичного файла: {len(binary_data)} байт")
    if args.test:
        for instr in instructions:
            print(format_bytes(encode_instruction(instr)))


if __name__ == "__main__":
    main()