/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import '../../../../shared/i18n';
import { DisplaySettings } from '../DisplaySettings';
import type { AppSettings } from '../../../../shared/types';

// Mock the settings store
vi.mock('../../../stores/settings-store', () => ({
  useSettingsStore: vi.fn(() => ({
    updateSettings: vi.fn()
  }))
}));

// Track onValueChange callbacks per Select instance
let selectCallbacks: Array<(v: string) => void> = [];

// Mock Radix Select to make it testable in jsdom (portals don't work in jsdom)
vi.mock('../../ui/select', () => {
  return {
    Select: ({ value, onValueChange, children }: { value: string; onValueChange: (v: string) => void; children: React.ReactNode }) => {
      selectCallbacks.push(onValueChange);
      const idx = selectCallbacks.length - 1;
      return <div data-testid={`select-root-${idx}`} data-value={value}>{children}</div>;
    },
    SelectTrigger: ({ id, children }: { id?: string; className?: string; children: React.ReactNode }) => (
      <button data-testid={`select-trigger-${id || 'unknown'}`}>{children}</button>
    ),
    SelectValue: () => null,
    SelectContent: ({ children }: { className?: string; children: React.ReactNode }) => (
      <div data-testid="select-content">{children}</div>
    ),
    SelectItem: ({ value, children }: { value: string; children: React.ReactNode }) => (
      <div role="option" data-testid={`select-item-${value}`} data-value={value}>
        {children}
      </div>
    )
  };
});

const defaultSettings: AppSettings = {
  uiScale: 100,
  logOrder: 'chronological',
  gpuAcceleration: 'auto'
} as AppSettings;

describe('DisplaySettings - GPU Acceleration Dropdown', () => {
  let mockOnSettingsChange: (settings: AppSettings) => void;

  beforeEach(() => {
    vi.clearAllMocks();
    selectCallbacks = [];
    mockOnSettingsChange = vi.fn();
  });

  it('should render the GPU acceleration dropdown with all 3 options', () => {
    render(
      <DisplaySettings settings={defaultSettings} onSettingsChange={mockOnSettingsChange} />
    );

    expect(screen.getByText('GPU Acceleration')).toBeInTheDocument();
    expect(screen.getByTestId('select-item-auto')).toBeInTheDocument();
    expect(screen.getByTestId('select-item-on')).toBeInTheDocument();
    expect(screen.getByTestId('select-item-off')).toBeInTheDocument();
  });

  it('should display the correct translated labels for each option', () => {
    render(
      <DisplaySettings settings={defaultSettings} onSettingsChange={mockOnSettingsChange} />
    );

    expect(screen.getByText('Auto (recommended)')).toBeInTheDocument();
    expect(screen.getByText('Always on')).toBeInTheDocument();
    expect(screen.getByText('Off')).toBeInTheDocument();
  });

  it('should display the current GPU acceleration value from settings', () => {
    const settingsWithOn: AppSettings = { ...defaultSettings, gpuAcceleration: 'on' };

    const { container } = render(
      <DisplaySettings settings={settingsWithOn} onSettingsChange={mockOnSettingsChange} />
    );

    // The GPU acceleration select is the second Select rendered (index 1, after logOrder)
    const gpuSelect = container.querySelector('[data-testid="select-root-1"]');
    expect(gpuSelect).toHaveAttribute('data-value', 'on');
  });

  it('should default to "auto" when gpuAcceleration is not set', () => {
    const settingsWithoutGpu: AppSettings = { ...defaultSettings, gpuAcceleration: undefined };

    const { container } = render(
      <DisplaySettings settings={settingsWithoutGpu} onSettingsChange={mockOnSettingsChange} />
    );

    const gpuSelect = container.querySelector('[data-testid="select-root-1"]');
    expect(gpuSelect).toHaveAttribute('data-value', 'auto');
  });

  it('should call onSettingsChange with gpuAcceleration "on" when selected', () => {
    render(
      <DisplaySettings settings={defaultSettings} onSettingsChange={mockOnSettingsChange} />
    );

    // selectCallbacks[1] is the GPU acceleration Select's onValueChange
    selectCallbacks[1]('on');

    expect(mockOnSettingsChange).toHaveBeenCalledWith(
      expect.objectContaining({ gpuAcceleration: 'on' })
    );
  });

  it('should call onSettingsChange with gpuAcceleration "off" when selected', () => {
    render(
      <DisplaySettings settings={defaultSettings} onSettingsChange={mockOnSettingsChange} />
    );

    selectCallbacks[1]('off');

    expect(mockOnSettingsChange).toHaveBeenCalledWith(
      expect.objectContaining({ gpuAcceleration: 'off' })
    );
  });

  it('should call onSettingsChange with gpuAcceleration "auto" when selected', () => {
    const settingsWithOff: AppSettings = { ...defaultSettings, gpuAcceleration: 'off' };

    render(
      <DisplaySettings settings={settingsWithOff} onSettingsChange={mockOnSettingsChange} />
    );

    selectCallbacks[1]('auto');

    expect(mockOnSettingsChange).toHaveBeenCalledWith(
      expect.objectContaining({ gpuAcceleration: 'auto' })
    );
  });

  it('should render the GPU acceleration description text', () => {
    render(
      <DisplaySettings settings={defaultSettings} onSettingsChange={mockOnSettingsChange} />
    );

    expect(
      screen.getByText('Use WebGL for terminal rendering (faster with many terminals)')
    ).toBeInTheDocument();
  });
});
