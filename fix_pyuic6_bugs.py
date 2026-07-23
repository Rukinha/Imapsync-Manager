#!/usr/bin/env python3
"""Corrige bugs de geração de código do pyuic6 (testado na 6.11.0)."""
from __future__ import annotations
import argparse, re
from pathlib import Path
from xml.etree import ElementTree as ET

SPACER_PATTERN = re.compile(
    r"QSpacerItem\(\s*"
    r"(QtWidgets\.QSizePolicy\.Policy\.\w+)\s*,\s*"
    r"(QtWidgets\.QSizePolicy\.Policy\.\w+)\s*\)"
)

def fix_spacers(text):
    count = 0
    def repl(m):
        nonlocal count
        h_policy, v_policy = m.group(1), m.group(2)
        horizontal = "Expanding" in h_policy
        w, h = (40, 20) if horizontal else (20, 40)
        count += 1
        return f"QSpacerItem({w}, {h}, {h_policy}, {v_policy})"
    return SPACER_PATTERN.sub(repl, text), count

def _python_literal(value_el):
    tag = value_el.tag
    text = (value_el.text or "").strip()
    if tag == "number": return text
    if tag == "double": return text
    if tag == "bool": return "True" if text.lower() == "true" else "False"
    if tag in ("string", "cstring"): return repr(text)
    return None

def collect_combobox_data(ui_root):
    result = {}
    for combo in ui_root.iter("widget"):
        if combo.get("class") != "QComboBox": continue
        name = combo.get("name")
        if not name: continue
        items = combo.findall("item")
        if not items: continue
        literals = []
        any_data = False
        for item in items:
            user_data_prop = None
            for prop in item.findall("property"):
                if prop.get("name") == "userData":
                    user_data_prop = prop
                    break
            if user_data_prop is None or len(user_data_prop) == 0:
                literals.append(None)
                continue
            value_el = user_data_prop[0]
            literal = _python_literal(value_el)
            literals.append(literal)
            if literal is not None: any_data = True
        if any_data: result[name] = literals
    return result

def fix_combobox_data(text, combo_data):
    count = 0
    lines = text.splitlines(keepends=True)
    for name, literals in combo_data.items():
        add_item_re = re.compile(rf"^\s*self\.{re.escape(name)}\.addItem\(")
        set_item_data_re = re.compile(rf"^\s*self\.{re.escape(name)}\.setItemData\(")
        if any(set_item_data_re.match(line) for line in lines): continue
        last_add_item_idx = None
        indent = ""
        for i, line in enumerate(lines):
            if add_item_re.match(line):
                last_add_item_idx = i
                indent = line[: len(line) - len(line.lstrip())]
        if last_add_item_idx is None: continue
        insert_lines = []
        for idx, literal in enumerate(literals):
            if literal is None: continue
            insert_lines.append(f"{indent}self.{name}.setItemData({idx}, {literal})\n")
            count += 1
        if insert_lines:
            lines[last_add_item_idx + 1:last_add_item_idx + 1] = insert_lines
    return "".join(lines), count

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ui", required=True)
    parser.add_argument("--py", required=True)
    args = parser.parse_args()
    ui_path, py_path = Path(args.ui), Path(args.py)
    if not ui_path.exists():
        print(f"[ERRO] .ui não encontrado: {ui_path}"); return 1
    if not py_path.exists():
        print(f"[ERRO] .py não encontrado: {py_path}"); return 1
    ui_root = ET.parse(ui_path).getroot()
    text = py_path.read_text(encoding="utf-8")
    text, spacer_count = fix_spacers(text)
    combo_data = collect_combobox_data(ui_root)
    text, combo_count = fix_combobox_data(text, combo_data)
    py_path.write_text(text, encoding="utf-8")
    print(f"[OK] {py_path}")
    print(f"     QSpacerItem corrigidos: {spacer_count}")
    print(f"     setItemData inseridos:  {combo_count}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
