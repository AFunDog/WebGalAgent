"""前端关键交互的源码契约测试。"""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_pipeline_view_keeps_dependency_guard_and_single_task_polling() -> None:
    source = _read("src/frontend/src/views/PipelineView.vue")

    assert "requiredPrevStepIndices" in source
    assert "startSingleTaskPolling" in source
    assert "api.createTask(content, {" in source
    assert "stepInputs: startStep.value > 0 ? stepInputs.value : undefined" in source


def test_tasks_view_keeps_multi_task_polling_lifecycle() -> None:
    source = _read("src/frontend/src/views/TasksView.vue")

    assert "startMultiTaskPolling" in source
    assert "stopAllMultiPolling" in source
    assert "onUnmounted(() => {" in source
    assert "if (t.status === 'running')" in source


def test_record_view_keeps_record_config_and_status_polling_contract() -> None:
    source = _read("src/frontend/src/views/RecordView.vue")

    assert "executable_path: config.executable_path || undefined" in source
    assert "stop_condition: config.stop_condition || undefined" in source
    assert "const startRes = await api.startRecord(recordConfig)" in source
    assert "const status = await api.getRecordStatus()" in source
