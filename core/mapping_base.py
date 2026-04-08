import json
import os
from pathlib import Path

class MappingStore:
    def __init__(self, base_dir: str):
        self.base_dir = os.path.abspath(base_dir)
        Path(self.base_dir).mkdir(parents=True, exist_ok=True)

    def _validate_name(self, name: str) -> str:
        if not isinstance(name, str):
            raise ValueError("Mapping name must be a string")

        candidate = name.strip()
        if candidate.endswith(".json"):
            candidate = candidate[:-5]
        candidate = candidate.strip()

        if not candidate:
            raise ValueError("Mapping name cannot be empty")

        # Prevent path traversal and invalid chars
        if any(ch in candidate for ch in "\/:"):
            raise ValueError("Mapping name cannot contain path separators")

        return candidate

    def _filename(self, name: str) -> str:
        safe_name = self._validate_name(name)
        return os.path.join(self.base_dir, f"{safe_name}.json")

    def list(self):
        files = []
        try:
            for entry in os.listdir(self.base_dir):
                if entry.lower().endswith('.json') and os.path.isfile(os.path.join(self.base_dir, entry)):
                    files.append(entry[:-5])
        except FileNotFoundError:
            Path(self.base_dir).mkdir(parents=True, exist_ok=True)
        files.sort()
        return files

    def read(self, name: str):
        path = self._filename(name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Mapping '{name}' does not exist")

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Stored mapping '{name}' contains invalid JSON: {exc}")

    def save(self, name: str, content: str, overwrite: bool = False):
        path = self._filename(name)
        if not overwrite and os.path.exists(path):
            raise FileExistsError(f"Mapping '{name}' already exists")

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {exc}")

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False)

        return parsed

    def update(self, current_name: str, new_name: str, content: str):
        current_safe_name = self._validate_name(current_name)
        new_safe_name = self._validate_name(new_name)

        current_path = self._filename(current_safe_name)
        new_path = self._filename(new_safe_name)

        if not os.path.exists(current_path):
            raise FileNotFoundError(f"Mapping '{current_name}' does not exist")

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {exc}")

        is_rename = current_safe_name != new_safe_name
        if is_rename and os.path.exists(new_path):
            raise FileExistsError(f"Mapping '{new_name}' already exists")

        with open(new_path, 'w', encoding='utf-8') as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False)

        if is_rename and os.path.exists(current_path):
            os.remove(current_path)

        return parsed

    def delete(self, name: str):
        path = self._filename(name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Mapping '{name}' does not exist")
        os.remove(path)
