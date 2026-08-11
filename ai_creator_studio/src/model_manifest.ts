import manifest from '../models/manifest.json';
import { ModelDefinition, ModelKind } from './model_manager';
import { ModelRequirement } from './hardware';

export interface ManifestFile { filename: string; size_bytes: number; sha256: string; url: string; }
export interface ManifestModel { id: string; version: string; kind: ModelKind; display_name: string; description: string; requirements: ModelRequirement; files: ManifestFile[]; sources: string[]; }
export interface ModelManifest { schema_version: number; generated_at: string; models: ManifestModel[]; }

export const MODEL_MANIFEST = manifest as ModelManifest;

export function manifestToDefinitions(): ModelDefinition[] {
  return MODEL_MANIFEST.models.map(model => ({
    id: model.id,
    name: model.display_name,
    kind: model.kind,
    description: model.description,
    sizeGb: model.files.reduce((sum, file) => sum + file.size_bytes, 0) / 1024 ** 3,
    requirements: model.requirements,
    state: 'available',
  }));
}

export function getManifestModel(id: string): ManifestModel | undefined {
  return MODEL_MANIFEST.models.find(model => model.id === id);
}
