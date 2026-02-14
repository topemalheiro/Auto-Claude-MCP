import { create } from "zustand";
import type { AppSettings } from "@/lib/data";
import { apiClient } from "@/lib/data";

const DEFAULT_SETTINGS: AppSettings = {
  theme: "system",
  sidebarCollapsed: false,
  onboardingCompleted: false,
};

interface SettingsState {
  settings: AppSettings;
  isLoading: boolean;

  // Actions
  updateSettings: (updates: Partial<AppSettings>) => void;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  settings: DEFAULT_SETTINGS,
  isLoading: true,

  updateSettings: (updates) =>
    set((state) => ({
      settings: { ...state.settings, ...updates },
    })),
}));

export async function loadSettings() {
  useSettingsStore.setState({ isLoading: true });
  try {
    const result = await apiClient.getSettings();
    useSettingsStore.setState({
      settings: { ...DEFAULT_SETTINGS, ...(result.settings as AppSettings) },
      isLoading: false,
    });
  } catch {
    // Use defaults if API not available
    useSettingsStore.setState({ isLoading: false });
  }
}

export async function saveSettings(updates: Partial<AppSettings>) {
  useSettingsStore.getState().updateSettings(updates);
  try {
    await apiClient.saveSettings(updates);
  } catch {
    // Settings saved locally even if API fails
  }
}
