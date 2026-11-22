"""CLI interpreter for UVM (Variant 13) - Stage 4."""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

OPCODE_LOAD_CONST = 111
OPCODE_READ_MEM = 17
OPCODE_WRITE_MEM = 46
OPCODE_UNARY_MINUS = 87

INSTRUCTION_SIZE_BYTES = 13
FIELD_A_BITS = 7
FIELD_B_BITS = 28
FIELD_C_ADDR_BITS = 28
FIELD_C_CONST_BITS = 14
FIELD_B_SHIFT = 7
FIELD_C_SHIFT = 35

FIELD_A_MASK = (1 << FIELD_A_BITS) - 1
FIELD_B_MASK = (1 << FIELD_B_BITS) - 1
FIELD_C_ADDR_MASK = (1 << FIELD_C_ADDR_BITS) - 1
FIELD_C_CONST_MASK = (1 << FIELD_C_CONST_BITS) - 1

MEMORY_SIZE = 4096
ZERO = 0
STEP_ONE = 1
RANGE_PARTS_COUNT = 2
RANGE_SEPARATOR = ":"
XML_INDENT = "  "


@dataclass(frozen=True)
class Instruction:
    """Decoded intermediate representation of a UVM instruction."""

    field_a: int
    field_b: int
    field_c: int


def parse_memory_range(range_text: str) -> tuple[int, int]:
    """Parse inclusive memory range in 'start:end' format."""
    parts = range_text.split(RANGE_SEPARATOR)
    if len(parts) != RANGE_PARTS_COUNT:
        raise ValueError(
            "Диапазон адресов должен иметь формат 'start:end'."
        )
    try:
        start = int(parts[ZERO])
        end = int(parts[STEP_ONE])
    except ValueError as exc:
        raise ValueError(
            "Границы диапазона должны быть целыми числами."
        ) from exc
    if start < ZERO or end < start or end >= MEMORY_SIZE:
        raise ValueError(
            f"Диапазон {start}:{end} вне границ памяти "
            f"[{ZERO}, {MEMORY_SIZE - STEP_ONE}]."
        )
    return start, end


def decode_word(word: int) -> Instruction:
    """Decode a packed integer instruction from unified memory."""
    field_a = word & FIELD_A_MASK
    field_b = (word >> FIELD_B_SHIFT) & FIELD_B_MASK
    if field_a == OPCODE_LOAD_CONST:
        field_c = (word >> FIELD_C_SHIFT) & FIELD_C_CONST_MASK
    else:
        field_c = (word >> FIELD_C_SHIFT) & FIELD_C_ADDR_MASK
    return Instruction(
        field_a=field_a,
        field_b=field_b,
        field_c=field_c,
    )


def load_program_into_memory(
    binary_data: bytes,
    memory: list[int],
) -> int:
    """Load binary machine code into the start of unified memory."""
    byte_count = len(binary_data)
    if byte_count % INSTRUCTION_SIZE_BYTES != ZERO:
        raise ValueError(
            "Размер бинарного файла не кратен 13 байтам."
        )
    instruction_count = byte_count // INSTRUCTION_SIZE_BYTES
    if instruction_count > len(memory):
        raise ValueError("Программа не помещается в память УВМ.")
    for index in range(instruction_count):
        offset = index * INSTRUCTION_SIZE_BYTES
        chunk = binary_data[offset:offset + INSTRUCTION_SIZE_BYTES]
        memory[index] = int.from_bytes(chunk, byteorder="little")
    return instruction_count


def validate_address(address: int, memory_size: int) -> None:
    """Ensure a memory address lies within valid unified memory bounds."""
    if address < ZERO or address >= memory_size:
        raise IndexError(
            f"Адрес памяти {address} вне диапазона "
            f"[{ZERO}, {memory_size - STEP_ONE}]."
        )


def execute_unary_minus(
    instr: Instruction,
    memory: list[int],
) -> None:
    """Execute ALU unary minus: mem[C] = -mem[mem[B]]."""
    mem_size = len(memory)
    validate_address(instr.field_b, mem_size)
    target_address = memory[instr.field_b]
    validate_address(target_address, mem_size)
    validate_address(instr.field_c, mem_size)
    memory[instr.field_c] = -memory[target_address]


def execute_instruction(
    instr: Instruction,
    memory: list[int],
) -> None:
    """Execute a single decoded instruction on unified memory."""
    mem_size = len(memory)
    if instr.field_a == OPCODE_LOAD_CONST:
        validate_address(instr.field_b, mem_size)
        memory[instr.field_b] = instr.field_c
        return
    if instr.field_a == OPCODE_READ_MEM:
        validate_address(instr.field_b, mem_size)
        validate_address(instr.field_c, mem_size)
        memory[instr.field_b] = memory[instr.field_c]
        return
    if instr.field_a == OPCODE_WRITE_MEM:
        validate_address(instr.field_b, mem_size)
        validate_address(instr.field_c, mem_size)
        memory[instr.field_c] = memory[instr.field_b]
        return
    if instr.field_a == OPCODE_UNARY_MINUS:
        execute_unary_minus(instr, memory)
        return
    raise ValueError(f"Неизвестный код операции: {instr.field_a}.")


def run_program(binary_data: bytes) -> list[int]:
    """Run main fetch-decode-execute loop over unified memory."""
    memory = [ZERO] * MEMORY_SIZE
    program_length = load_program_into_memory(binary_data, memory)
    for pc in range(program_length):
        instruction = decode_word(memory[pc])
        execute_instruction(instruction, memory)
    return memory


def save_memory_dump_xml(
    memory: list[int],
    start: int,
    end: int,
    dump_path: Path,
) -> None:
    """Export the requested memory address range to an XML file."""
    root = ET.Element("memory")
    for address in range(start, end + STEP_ONE):
        cell = ET.SubElement(root, "cell", address=str(address))
        cell.text = str(memory[address])
    tree = ET.ElementTree(root)
    ET.indent(tree, space=XML_INDENT)
    dump_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(dump_path, encoding="utf-8", xml_declaration=True)


def build_arg_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser for the UVM interpreter."""
    parser = argparse.ArgumentParser(
        description="Интерпретатор УВМ (вариант 13)."
    )
    parser.add_argument(
        "binary_path",
        type=Path,
        help="Путь к бинарному файлу с программой.",
    )
    parser.add_argument(
        "dump_path",
        type=Path,
        help="Путь к выходному XML-файлу дампа памяти.",
    )
    parser.add_argument(
        "mem_range",
        type=str,
        help="Диапазон адресов памяти для дампа (формат start:end).",
    )
    return parser


def main() -> None:
    """Entry point for the UVM interpreter CLI application."""
    parser = build_arg_parser()
    args = parser.parse_args()
    try:
        start, end = parse_memory_range(args.mem_range)
        binary_data = args.binary_path.read_bytes()
        memory = run_program(binary_data)
        save_memory_dump_xml(memory, start, end, args.dump_path)
    except (OSError, ValueError, IndexError) as exc:
        sys.exit(f"Ошибка: {exc}")


if __name__ == "__main__":
    main()