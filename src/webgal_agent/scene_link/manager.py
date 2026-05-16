"""软链接管理器：创建和管理 WebGal 场景软链接。"""

from __future__ import annotations

import pathlib
import subprocess
import shutil
from dataclasses import dataclass


@dataclass
class LinkResult:
    """软链接创建结果。"""

    success: bool
    message: str
    link_path: str | None = None
    target_path: str | None = None


class SceneLinkManager:
    """管理 WebGal 场景目录的软链接。

    在 Windows 上使用 mklink /D 命令创建目录符号链接，
    将任务结果目录链接到 WebGal 游戏目录的 scene 文件夹。
    """

    def __init__(
        self,
        result_base_dir: str | pathlib.Path = "data/tasks",
        default_link_root: str | pathlib.Path = r"D:\Data\WebGal",
    ) -> None:
        self._result_base_dir = pathlib.Path(result_base_dir)
        self._default_link_root = pathlib.Path(default_link_root)

    @property
    def result_base_dir(self) -> pathlib.Path:
        return self._result_base_dir

    @property
    def default_link_root(self) -> pathlib.Path:
        return self._default_link_root

    def get_result_path(self, task_id: str) -> pathlib.Path:
        """获取指定任务的结果目录路径。"""
        return self._result_base_dir / task_id / "result"

    def get_default_link_path(self) -> pathlib.Path:
        """获取默认的软链接路径。"""
        return self._default_link_root / "scene"

    def create_link(
        self,
        task_id: str,
        link_path: str | pathlib.Path | None = None,
        force: bool = False,
    ) -> LinkResult:
        """创建软链接。

        Args:
            task_id: 任务 ID
            link_path: 软链接路径，默认使用 D:\\Data\\WebGal\\scene
            force: 是否强制覆盖已存在的链接

        Returns:
            LinkResult: 创建结果
        """
        result_dir = self.get_result_path(task_id)

        if not result_dir.exists():
            return LinkResult(
                success=False,
                message=f"任务结果目录不存在: {result_dir}",
            )

        if link_path is None:
            link_path = self.get_default_link_path()
        else:
            link_path = pathlib.Path(link_path)

        # 检查链接是否已存在
        if link_path.exists() or link_path.is_symlink():
            if not force:
                # 检查是否是符号链接
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
                    )
                return LinkResult(
                    success=False,
                    message=f"路径已存在且不是符号链接: {link_path}",
                )
            # 删除现有链接
            try:
                if link_path.is_symlink():
                    link_path.unlink()
                elif link_path.is_dir():
                    shutil.rmtree(link_path)
                else:
                    link_path.unlink()
            except Exception as e:
                return LinkResult(
                    success=False,
                    message=f"删除现有链接失败: {e}",
                )

        # 确保父目录存在
        link_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建符号链接
        try:
            self._create_symlink_win(str(result_dir), str(link_path))
            return LinkResult(
                success=True,
                message="软链接创建成功",
                link_path=str(link_path),
                target_path=str(result_dir),
            )
        except Exception as e:
            return LinkResult(
                success=False,
                message=f"创建软链接失败: {e}",
            )

    def _create_symlink_win(self, target: str, link: str) -> None:
        """Windows 下创建目录符号链接。

        使用 cmd /c mklink /D 命令创建符号链接。
        需要管理员权限或启用开发者模式。
        """
        subprocess.run(
            ["cmd", "/c", "mklink", "/D", link, target],
            check=True,
            capture_output=True,
            text=True,
        )

    def remove_link(self, link_path: str | pathlib.Path | None = None) -> LinkResult:
        """删除软链接。

        Args:
            link_path: 软链接路径，默认使用 D:\\Data\\WebGal\\scene

        Returns:
            LinkResult: 删除结果
        """
        if link_path is None:
            link_path = self.get_default_link_path()
        else:
            link_path = pathlib.Path(link_path)

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

    def get_link_status(
        self, link_path: str | pathlib.Path | None = None
    ) -> dict:
        """获取软链接状态。

        Returns:
            dict: 包含链接状态的字典
        """
        if link_path is None:
            link_path = self.get_default_link_path()
        else:
            link_path = pathlib.Path(link_path)

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
