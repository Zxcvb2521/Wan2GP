import { ModelDefinition } from './model_manager';

export interface ModelSource {
  url: string;
  filename: string;
  sha256?: string;
}

export interface ModelInstallRecord {
  modelId: string;
  path: string;
  installedAt: string;
  sizeBytes: number;
  verified: boolean;
}

export interface ModelDownloadProgress {
  modelId: string;
  downloadedBytes: number;
  totalBytes: number;
  status: 'queued' | 'downloading' | 'verifying' | 'installed' | 'error';
  error?: string;
}

/**
 * Local model-store contract.
 * Network/download implementation is deliberately kept outside the UI so
 * the same API can later be backed by Hugging Face, GitHub releases or a
 * private mirror without changing Model Manager.
 */
export interface ModelStore {
  listInstalled(): Promise<ModelInstallRecord[]>;
  install(model: ModelDefinition, source: ModelSource, onProgress?: (p: ModelDownloadProgress) => void): Promise<ModelInstallRecord>;
  remove(modelId: string): Promise<void>;
  getPath(modelId: string): Promise<string | null>;
}

export function canInstallModel(model: ModelDefinition, freeDiskGb: number): { ok: boolean; reason?: string } {
  if (freeDiskGb < model.sizeGb) {
    return { ok: false, reason: `Недостаточно места: требуется около ${model.sizeGb} ГБ, доступно ${freeDiskGb.toFixed(1)} ГБ.` };
  }
  return { ok: true };
}
