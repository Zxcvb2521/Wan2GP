import { HardwareInfo, ModelCompatibility, ModelRequirement, checkModelCompatibility } from './hardware';

export type ModelKind = 'image' | 'video' | 'llm' | 'tts' | 'music';
export type ModelState = 'installed' | 'available' | 'downloading' | 'error';

export interface ModelDefinition {
  id: string;
  name: string;
  kind: ModelKind;
  description: string;
  sizeGb: number;
  requirements: ModelRequirement;
  state: ModelState;
  path?: string;
}

export interface ModelStatus extends ModelDefinition {
  compatibility: ModelCompatibility;
}

/** Registry metadata only. Actual model files are managed separately. */
export const MODEL_CATALOG: ModelDefinition[] = [
  {
    id: 'wan2gp-image',
    name: 'Wan — изображения',
    kind: 'image',
    description: 'Генерация изображений через WanGP.',
    sizeGb: 6,
    requirements: { minVramGb: 6, recommendedVramGb: 12, minRamGb: 16, cpuAllowed: false, vendors: ['nvidia'] },
    state: 'available',
  },
  {
    id: 'wan2gp-video',
    name: 'Wan — видео',
    kind: 'video',
    description: 'Генерация видео через WanGP.',
    sizeGb: 12,
    requirements: { minVramGb: 8, recommendedVramGb: 16, minRamGb: 24, cpuAllowed: false, vendors: ['nvidia'] },
    state: 'available',
  },
  {
    id: 'local-llm',
    name: 'Локальная LLM',
    kind: 'llm',
    description: 'Текстовые модели для сценариев и промптов.',
    sizeGb: 5,
    requirements: { minRamGb: 8, cpuAllowed: true },
    state: 'available',
  },
  {
    id: 'local-tts',
    name: 'Локальный TTS',
    kind: 'tts',
    description: 'Синтез речи для озвучивания сцен.',
    sizeGb: 2,
    requirements: { minRamGb: 8, cpuAllowed: true },
    state: 'available',
  },
  {
    id: 'local-music',
    name: 'Локальная музыка',
    kind: 'music',
    description: 'Генерация музыкального сопровождения.',
    sizeGb: 4,
    requirements: { minRamGb: 16, cpuAllowed: true },
    state: 'available',
  },
];

export function getModelStatuses(hardware: HardwareInfo): ModelStatus[] {
  return MODEL_CATALOG.map(model => ({
    ...model,
    compatibility: checkModelCompatibility(hardware, model.requirements),
  }));
}

export function getRecommendedModels(hardware: HardwareInfo): ModelStatus[] {
  return getModelStatuses(hardware).filter(model => model.compatibility.compatible);
}
