export interface PipelineStepDef {
  name: string
  label: string
  deps?: string[]
}

export const PIPELINE_STEPS: PipelineStepDef[] = [
  { name: 'outline_writer', label: '大纲编写', deps: [] },
  { name: 'script_writer', label: '剧本生成', deps: ['outline_writer'] },
  { name: 'script_converter', label: '脚本转换', deps: ['script_writer'] },
]

export const AGENT_LABELS: Record<string, string> = {
  outline_writer: '大纲编写',
  script_writer: '剧本生成',
  script_converter: '脚本转换',
}
