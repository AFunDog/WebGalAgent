"""软链接管理器：创建和管理 WebGal 场景软链接。"""

from __future__ import annotations

import pathlib
import subprocess
from dataclasses import dataclass


@dataclass
class LinkResult:
    """软链接创建结果。"""

    success: bool
    message: str
    link_path: str | None = None
    target_path: str | None = None


class SceneLinkManager:
    """管理 WebGal 场景目录的软链接。"""

    def __init__(
        self,
        result_base_dir: str | pathlib.Path = "data/tasks",
        default_link_path: str | pathlib.Path = r"D:\Data\WebGal\games\MyGO3.0.0\game\scene",
        default_scene_source_path: str | pathlib.Path = r"D:\Data\WebGal\scene",
    ) -> None:
        self._result_base_dir = pathlib.Path(result_base_dir)
        self._default_link_path = pathlib.Path(default_link_path)
        self._default_scene_source_path = pathlib.Path(default_scene_source_path)

    @property
    def result_base_dir(self) -> pathlib.Path:
        return self._result_base_dir

    @property
    def default_link_path(self) -> pathlib.Path:
        return self._default_link_path

    @property
    def default_scene_source_path(self) -> pathlib.Path:
        return self._default_scene_source_path

    def get_result_path(self, task_id: str) -> pathlib.Path:
        """获取指定任务的结果目录路径。"""
        return self._result_base_dir / task_id / "result"

    def get_default_link_path(self) -> pathlib.Path:
        """获取默认的软链接路径。"""
        return self._default_link_path

    def get_default_scene_source_path(self) -> pathlib.Path:
        """获取重置时应恢复到的默认场景目录。"""
        return self._default_scene_source_path

    def _normalize_link_path(self, link_path: str | pathlib.Path | None) -> pathlib.Path:
        if link_path is None:
            return self.get_default_link_path()
        return pathlib.Path(link_path)

    def _create_symlink_win(self, target: str, link: str) -> None:
        """Windows 下创建目录符号链接。"""
        target_abs = str(pathlib.Path(target).resolve())
        subprocess.run(
            ["cmd", "/c", "mklink", "/D", link, target_abs],
            check=True,
            capture_output=True,
            text=True,
        )

    def _replace_symlink(self, link_path: pathlib.Path, target_path: pathlib.Path) -> LinkResult:
        if link_path.exists() or link_path.is_symlink():
            try:
                if link_path.is_symlink():
                    link_path.unlink()
                else:
                    return LinkResult(
                        success=False,
                        message=f"拒绝覆盖非符号链接路径: {link_path}",
                    )
            except Exception as e:
                return LinkResult(
                    success=False,
                    message=f"删除现有链接失败: {e}",
                )

        link_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._create_symlink_win(str(target_path), str(link_path))
            return LinkResult(
                success=True,
                message="软链接创建成功",
                link_path=str(link_path),
                target_path=str(target_path),
            )
        except Exception as e:
            return LinkResult(
                success=False,
                message=f"创建软链接失败: {e}",
            )

    def create_link(
        self,
        task_id: str,
        link_path: str | pathlib.Path | None = None,
        force: bool = False,
    ) -> LinkResult:
        """将游戏 scene 目录切到任务结果目录。"""
        result_dir = self.get_result_path(task_id)
        if not result_dir.exists():
            return LinkResult(
                success=False,
                message=f"任务结果目录不存在: {result_dir}",
            )

        link_path = self._normalize_link_path(link_path)

        if link_path.exists() or link_path.is_symlink():
            if not force:
                if link_path.is_symlink():
                    current_target = link_path.resolve()
                    if current_target == result_dir.resolve():
                        return LinkResult(
                            success=True,
                            message="软链接已存在且指向正确的目录",
                            link_path=str(link_path),
                            target_path=str(result_dir),
                        )
                    return LinkResult(
                        success=False,
                        message=f"软链接已存在但指向其他位置: {current_target}",
                        link_path=str(link_path),
                        target_path=str(current_target),
                    )
                return LinkResult(
                    success=False,
                    message=f"路径已存在且不是符号链接: {link_path}",
                    link_path=str(link_path),
                )

        return self._replace_symlink(link_path, result_dir)

    def remove_link(self, link_path: str | pathlib.Path | None = None) -> LinkResult:
        """删除软链接本身。"""
        link_path = self._normalize_link_path(link_path)

        if not link_path.exists():
            return LinkResult(
                success=False,
                message=f"路径不存在: {link_path}",
            )

        if not link_path.is_symlink():
            return LinkResult(
                success=False,
                message=f"路径不是符号链接: {link_path}",
            )

        try:
            link_path.unlink()
            return LinkResult(
                success=True,
                message="软链接已删除",
                link_path=str(link_path),
            )
        except Exception as e:
            return LinkResult(
                success=False,
                message=f"删除软链接失败: {e}",
            )

    def reset_link(self, link_path: str | pathlib.Path | None = None) -> LinkResult:
        """将场景软链接恢复到默认场景目录。"""
        link_path = self._normalize_link_path(link_path)
        source_path = self.get_default_scene_source_path()

        if not source_path.exists():
            return LinkResult(
                success=False,
                message=f"默认场景目录不存在: {source_path}",
                link_path=str(link_path),
                target_path=str(source_path),
            )

        if link_path.is_symlink():
            try:
                current_target = link_path.resolve()
            except Exception:
                current_target = None
            if current_target == source_path.resolve():
                return LinkResult(
                    success=True,
                    message="软链接已指向默认场景目录",
                    link_path=str(link_path),
                    target_path=str(source_path),
                )

        return self._replace_symlink(link_path, source_path)

    def get_link_status(self, link_path: str | pathlib.Path | None = None) -> dict:
        """获取软链接状态。"""
        link_path = self._normalize_link_path(link_path)

        result = {
            "path": str(link_path),
            "exists": link_path.exists(),
            "is_symlink": link_path.is_symlink() if link_path.exists() else False,
            "target": None,
            "valid": False,
        }

        if link_path.is_symlink():
            try:
                result["target"] = str(link_path.resolve())
                result["valid"] = link_path.resolve().exists()
            except Exception:
                result["target"] = "（无法解析）"

        return result
