import { onUnmounted } from 'vue'
import { api } from '../api'
import type { Task } from '../types'

export function useTaskPolling() {
  let singlePollTimer: ReturnType<typeof setInterval> | null = null
  const multiPollTimers = new Map<string, ReturnType<typeof setInterval>>()

  function stopSinglePolling() {
    if (singlePollTimer !== null) {
      clearInterval(singlePollTimer)
      singlePollTimer = null
    }
  }

  function startSingleTaskPolling(taskId: string, onUpdate: (task: Task) => void) {
    if (singlePollTimer !== null) return
    singlePollTimer = setInterval(async () => {
      try {
        const task = await api.getTask(taskId)
        onUpdate(task)
        if (task.status !== 'running') {
          stopSinglePolling()
        }
      } catch {
        stopSinglePolling()
      }
    }, 1500)
  }

  function startMultiTaskPolling(taskId: string, onUpdate: (task: Task) => void) {
    if (multiPollTimers.has(taskId)) return
    const timer = setInterval(async () => {
      try {
        const task = await api.getTask(taskId)
        onUpdate(task)
        if (task.status !== 'running') {
          clearInterval(timer)
          multiPollTimers.delete(taskId)
        }
      } catch {
        clearInterval(timer)
        multiPollTimers.delete(taskId)
      }
    }, 1500)
    multiPollTimers.set(taskId, timer)
  }

  function stopAllMultiPolling() {
    multiPollTimers.forEach(timer => clearInterval(timer))
    multiPollTimers.clear()
  }

  onUnmounted(() => {
    stopSinglePolling()
    stopAllMultiPolling()
  })

  return {
    startSingleTaskPolling,
    stopSinglePolling,
    startMultiTaskPolling,
    stopAllMultiPolling,
  }
}
