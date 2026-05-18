import { AGENT_LABELS } from '../constants/pipeline'
import type { Task } from '../types'

export function statusBadgeClass(status: string): string {
  switch (status) {
    case 'completed': return 'badge-success'
    case 'running': return 'badge-warning'
    case 'paused': return 'badge-info'
    case 'failed': return 'badge-danger'
    case 'cancelled': return 'badge-danger'
    default: return 'badge-muted'
  }
}

export function statusLabel(status: string): string {
  switch (status) {
    case 'completed': return '已完成'
    case 'running': return '执行中'
    case 'paused': return '等待下一步'
    case 'pending': return '待开始'
    case 'failed': return '失败'
    case 'cancelled': return '已取消'
    default: return status
  }
}

export function getStepStatus(task: Task, idx: number): string {
  if (idx < task.current_step) return 'done'
  if (idx === task.current_step) {
    if (task.status === 'running') return 'running'
    if (task.status === 'completed') return 'done'
    return 'ready'
  }
  return 'pending'
}

export function getStepStatusText(task: Task, idx: number): string {
  const status = getStepStatus(task, idx)
  switch (status) {
    case 'done': return '已完成'
    case 'running': return '执行中'
    case 'ready': return '待执行'
    default: return '等待中'
  }
}

export function formatTokenCount(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}

export function agentLabel(name: string): string {
  return AGENT_LABELS[name] ?? name
}
