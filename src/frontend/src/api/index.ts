import { knowledgeApi } from './knowledge'
import { workflowApi } from './workflows'
import { tasksApi } from './tasks'
import { providersApi } from './providers'
import { sceneLinkApi } from './sceneLink'
import { recordApi } from './record'

export const api = {
  ...knowledgeApi,
  ...workflowApi,
  ...tasksApi,
  ...providersApi,
  ...sceneLinkApi,
  ...recordApi,
}
