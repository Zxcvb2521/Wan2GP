import { checkModelCompatibility, HardwareInfo, ModelRequirement } from './hardware';

export interface StudioModel {
  model_type: string;
  name?: string;
  requirements?: ModelRequirement;
  availability?: { available?: boolean };
}

export function annotateModels(hw: HardwareInfo, models: StudioModel[]) {
  return models.map((model) => ({
    ...model,
    compatibility: checkModelCompatibility(hw, model.requirements || {}),
  }));
}

export function recommendedModel<T extends StudioModel>(hw: HardwareInfo, models: T[]): T | undefined {
  const annotated = annotateModels(hw, models);
  const preferred = annotated.find(
    (m) => m.availability?.available !== false && m.compatibility.level === 'recommended',
  );
  if (preferred) return preferred as T;

  const possible = annotated.find(
    (m) => m.availability?.available !== false && m.compatibility.level === 'possible',
  );
  return possible as T | undefined;
}
