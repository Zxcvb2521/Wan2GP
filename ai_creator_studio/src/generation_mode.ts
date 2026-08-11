export type GenerationMode = 'image' | 'video';

export interface GenerationSettings {
  model_type?: string;
  width?: number;
  height?: number;
  num_inference_steps?: number;
  seed?: number;
  [key: string]: unknown;
}

export interface GenerationRequest {
  mode: GenerationMode;
  prompt: string;
  settings?: GenerationSettings;
  project_id?: string;
}

export async function submitGeneration(api: string, request: GenerationRequest) {
  const endpoint = request.mode === 'video' ? '/generate/video' : '/generate/image';
  const response = await fetch(`${api}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || 'Не удалось запустить генерацию');
  }
  if (!payload.job_id) {
    throw new Error('Движок не вернул идентификатор задачи');
  }
  return payload as { ok: boolean; job_id: string };
}
