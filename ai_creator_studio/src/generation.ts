export type GenerationMode = 'image' | 'video';

export type GenerationSettings = Record<string, unknown> & {
  model_type?: string;
};

export type GenerationRequest = {
  mode: GenerationMode;
  prompt: string;
  settings?: GenerationSettings;
  project_id?: string;
};

export type GenerationJob = {
  id: string;
  status: string;
  progress: number;
  phase?: string;
  status_text?: string;
  current_step?: number;
  total_steps?: number;
  model_type?: string;
  model_name?: string;
  runtime?: Record<string, unknown>;
  result?: Record<string, unknown>;
  error?: string;
};

const API = 'http://127.0.0.1:18765';

function endpoint(mode: GenerationMode): string {
  return mode === 'video' ? `${API}/generate/video` : `${API}/generate/image`;
}

export async function createGeneration(request: GenerationRequest): Promise<string> {
  const prompt = request.prompt.trim();
  if (!prompt) throw new Error('Введите описание для генерации');

  const response = await fetch(endpoint(request.mode), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt,
      settings: request.settings ?? {},
      project_id: request.project_id,
    }),
  });

  const data = await response.json();
  if (!response.ok || !data.job_id) {
    throw new Error(data.error || 'Не удалось создать задачу генерации');
  }
  return data.job_id as string;
}

export async function getGenerationJob(jobId: string): Promise<GenerationJob> {
  const response = await fetch(`${API}/jobs/${encodeURIComponent(jobId)}`);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Не удалось получить состояние генерации');
  return data as GenerationJob;
}

export async function cancelGeneration(jobId: string): Promise<void> {
  const response = await fetch(`${API}/jobs/${encodeURIComponent(jobId)}/cancel`, {
    method: 'POST',
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Не удалось отменить генерацию');
}

export async function waitForGeneration(
  jobId: string,
  onUpdate?: (job: GenerationJob) => void,
  intervalMs = 350,
  maxPolls = 1440,
): Promise<GenerationJob> {
  let last: GenerationJob | null = null;

  for (let i = 0; i < maxPolls; i += 1) {
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
    last = await getGenerationJob(jobId);
    onUpdate?.(last);

    if (['completed', 'failed', 'cancelled'].includes(last.status)) return last;
  }

  throw new Error('Истекло время ожидания генерации');
}

export function mediaFiles(job: GenerationJob): string[] {
  const result = job.result ?? {};
  const files = result.generated_files ?? result.files ?? [];
  return Array.isArray(files) ? files.filter((value): value is string => typeof value === 'string') : [];
}
