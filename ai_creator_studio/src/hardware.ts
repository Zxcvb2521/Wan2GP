export type GpuVendor = 'nvidia' | 'amd' | 'intel' | 'apple' | 'unknown';
export type PerformanceProfile = 'high' | 'balanced' | 'economy' | 'cpu';

export interface HardwareInfo {
  platform: string;
  arch: string;
  cpu: string;
  ram_gb: number;
  gpu: {
    vendor: GpuVendor;
    name: string;
    vram_gb: number;
    accelerator: boolean;
    driver?: string;
    cuda?: string;
  };
  profile: PerformanceProfile;
}

export interface ModelRequirement {
  min_vram_gb?: number;
  recommended_vram_gb?: number;
  min_ram_gb?: number;
  cpu_supported?: boolean;
  vendors?: GpuVendor[];
}

export interface ModelCompatibility {
  compatible: boolean;
  level: 'recommended' | 'possible' | 'unsupported';
  reasons: string[];
}

export function choosePerformanceProfile(hw: HardwareInfo): PerformanceProfile {
  if (!hw.gpu.accelerator || hw.gpu.vram_gb < 4) return 'cpu';
  if (hw.gpu.vram_gb >= 20) return 'high';
  if (hw.gpu.vram_gb >= 10) return 'balanced';
  return 'economy';
}

export function checkModelCompatibility(hw: HardwareInfo, req: ModelRequirement): ModelCompatibility {
  const reasons: string[] = [];
  const vram = hw.gpu.vram_gb;
  const ram = hw.ram_gb;

  if (req.min_ram_gb && ram < req.min_ram_gb) {
    reasons.push(`Нужно минимум ${req.min_ram_gb} ГБ ОЗУ, доступно ${ram} ГБ.`);
  }

  if (req.vendors?.length && hw.gpu.accelerator && !req.vendors.includes(hw.gpu.vendor)) {
    reasons.push(`Модель рассчитана на: ${req.vendors.join(', ')}.`);
  }

  if (req.min_vram_gb && vram < req.min_vram_gb && !req.cpu_supported) {
    reasons.push(`Нужно минимум ${req.min_vram_gb} ГБ видеопамяти, доступно ${vram} ГБ.`);
  }

  if (reasons.length) {
    return { compatible: false, level: 'unsupported', reasons };
  }

  if (req.recommended_vram_gb && vram < req.recommended_vram_gb) {
    return {
      compatible: true,
      level: 'possible',
      reasons: [`Работа возможна, но рекомендуется ${req.recommended_vram_gb} ГБ VRAM.`],
    };
  }

  return { compatible: true, level: 'recommended', reasons: [] };
}

/**
 * Нормализует данные hardware detector backend перед передачей в UI.
 * Никакой конкретной модели GPU здесь не зашивается.
 */
export function normalizeHardware(raw: Partial<HardwareInfo>): HardwareInfo {
  const hw: HardwareInfo = {
    platform: raw.platform || 'unknown',
    arch: raw.arch || 'unknown',
    cpu: raw.cpu || 'Неизвестный процессор',
    ram_gb: Math.max(0, Number(raw.ram_gb || 0)),
    gpu: {
      vendor: raw.gpu?.vendor || 'unknown',
      name: raw.gpu?.name || 'Ускоритель не обнаружен',
      vram_gb: Math.max(0, Number(raw.gpu?.vram_gb || 0)),
      accelerator: Boolean(raw.gpu?.accelerator),
      driver: raw.gpu?.driver,
      cuda: raw.gpu?.cuda,
    },
    profile: 'cpu',
  };

  hw.profile = choosePerformanceProfile(hw);
  return hw;
}
