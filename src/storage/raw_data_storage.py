"""APIから取得した未加工データのローカル保存。"""

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class RawDataStorage:
    """未加工のAPIレスポンスをJSONまたはCSVとして保存する。"""

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir).expanduser().resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_json(
        self,
        source: str,
        category: str,
        data: Any,
        file_name: str,
    ) -> Path:
        """データをUTF-8のJSON原本として保存し、保存先を返す。"""

        destination = self._build_destination(
            source, category, file_name, extension=".json"
        )
        temporary_path = destination.with_suffix(f"{destination.suffix}.tmp")
        try:
            with temporary_path.open("w", encoding="utf-8", newline="\n") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
                file.write("\n")
            temporary_path.replace(destination)
        except (OSError, TypeError, ValueError):
            temporary_path.unlink(missing_ok=True)
            logger.exception("JSON原本の保存に失敗しました: %s", destination)
            raise

        logger.info("JSON原本を保存しました: %s", destination)
        return destination

    def save_csv(
        self,
        source: str,
        category: str,
        dataframe: pd.DataFrame,
        file_name: str,
    ) -> Path:
        """DataFrameをUTF-8のCSV原本として保存し、保存先を返す。"""

        destination = self._build_destination(
            source, category, file_name, extension=".csv"
        )
        temporary_path = destination.with_suffix(f"{destination.suffix}.tmp")
        try:
            dataframe.to_csv(temporary_path, index=False, encoding="utf-8")
            temporary_path.replace(destination)
        except (OSError, TypeError, ValueError):
            temporary_path.unlink(missing_ok=True)
            logger.exception("CSV原本の保存に失敗しました: %s", destination)
            raise

        logger.info("CSV原本を保存しました: %s", destination)
        return destination

    def load_json(self, path: str | Path) -> Any:
        """保存済みJSONを読み込み、Pythonオブジェクトとして返す。"""

        source_path = Path(path).expanduser()
        if not source_path.is_absolute():
            source_path = self.base_dir / source_path
        source_path = source_path.resolve()
        self._ensure_within_base_dir(source_path)

        with source_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _build_destination(
        self,
        source: str,
        category: str,
        file_name: str,
        *,
        extension: str,
    ) -> Path:
        """安全な保存先を組み立て、必要なディレクトリを作成する。"""

        source = self._validate_path_segment(source, "source")
        category = self._validate_path_segment(category, "category")
        file_name = self._validate_path_segment(file_name, "file_name")

        file_path = Path(file_name)
        if file_path.suffix.lower() != extension:
            file_path = file_path.with_suffix(extension)

        destination = (self.base_dir / source / category / file_path).resolve()
        self._ensure_within_base_dir(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        return destination

    @staticmethod
    def _validate_path_segment(value: str, field_name: str) -> str:
        """空文字、絶対パス、親ディレクトリ参照を拒否する。"""

        normalized = value.strip()
        path = Path(normalized)
        if (
            not normalized
            or path.is_absolute()
            or path.name != normalized
            or normalized in {".", ".."}
        ):
            raise ValueError(f"{field_name} must be a single safe path segment")
        return normalized

    def _ensure_within_base_dir(self, path: Path) -> None:
        """操作対象がrawデータ保存領域の外へ出ないことを検証する。"""

        if not path.is_relative_to(self.base_dir):
            raise ValueError("path must be inside the raw data directory")
