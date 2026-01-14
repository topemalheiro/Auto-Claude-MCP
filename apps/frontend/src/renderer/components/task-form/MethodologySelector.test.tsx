/**
 * @vitest-environment jsdom
 */
/**
 * Tests for MethodologySelector component
 */
import { render, screen, fireEvent, within, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { TooltipProvider } from '../ui/tooltip';
import { MethodologySelector } from './MethodologySelector';

// Helper to wrap component with TooltipProvider
function renderWithProviders(ui: React.ReactElement) {
  return render(<TooltipProvider>{ui}</TooltipProvider>);
}

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'tasks:methodology.label': 'Methodology',
        'tasks:methodology.helpText': 'Choose which methodology plugin to use for task execution.',
        'tasks:methodology.placeholder': 'Select methodology',
        'tasks:methodology.loading': 'Loading methodologies...',
        'tasks:methodology.noMethodologies': 'No methodologies available',
        'tasks:methodology.verified': 'Verified',
        'tasks:methodology.unverified': 'Community',
        'tasks:methodology.unverifiedWarning': 'Community plugins are not verified by the Auto Claude team. Use with caution.'
      };
      return translations[key] || key;
    }
  })
}));

// Default mock for useMethodologies - verified methodology
const mockUseMethodologies = vi.fn();
vi.mock('./useMethodologies', () => ({
  useMethodologies: () => mockUseMethodologies()
}));

describe('MethodologySelector', () => {
  const defaultProps = {
    value: 'native',
    onChange: vi.fn()
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Default: return verified methodology
    mockUseMethodologies.mockReturnValue({
      methodologies: [
        {
          name: 'native',
          version: '1.0.0',
          description: 'Built-in methodology with spec creation and implementation phases',
          author: 'Auto Claude',
          complexity_levels: ['quick', 'standard', 'complex'],
          execution_modes: ['full_auto', 'semi_auto'],
          is_verified: true,
        }
      ],
      isLoading: false,
      error: null,
      refetch: vi.fn()
    });
  });

  it('renders with label and help text', () => {
    renderWithProviders(<MethodologySelector {...defaultProps} />);

    expect(screen.getByText('Methodology')).toBeInTheDocument();
    expect(screen.getByText(/choose which methodology plugin/i)).toBeInTheDocument();
  });

  it('displays native as selected value with verified badge', () => {
    renderWithProviders(<MethodologySelector {...defaultProps} />);

    const trigger = screen.getByRole('combobox');
    expect(trigger).toHaveTextContent(/native/i);
    expect(trigger).toHaveTextContent(/verified/i);
  });

  it('shows methodology options when dropdown is opened', async () => {
    renderWithProviders(<MethodologySelector {...defaultProps} />);

    // Open the dropdown
    const trigger = screen.getByRole('combobox');
    fireEvent.click(trigger);

    // Wait for dropdown to open and check options
    const listbox = await screen.findByRole('listbox');
    expect(within(listbox).getByText(/native/i)).toBeInTheDocument();
  });

  it('shows descriptions for methodology options', async () => {
    renderWithProviders(<MethodologySelector {...defaultProps} />);

    // Open the dropdown
    const trigger = screen.getByRole('combobox');
    fireEvent.click(trigger);

    // Check description is present
    const listbox = await screen.findByRole('listbox');
    expect(within(listbox).getByText(/built-in methodology/i)).toBeInTheDocument();
  });

  it('shows verified badge for verified methodologies', async () => {
    renderWithProviders(<MethodologySelector {...defaultProps} />);

    // Open the dropdown
    const trigger = screen.getByRole('combobox');
    fireEvent.click(trigger);

    // Check verified badge is present in the dropdown
    const listbox = await screen.findByRole('listbox');
    expect(within(listbox).getByText('Verified')).toBeInTheDocument();
  });

  it('calls onChange when an option is selected', async () => {
    const onChange = vi.fn();
    // Start with empty value so selecting native triggers onChange
    renderWithProviders(<MethodologySelector value="" onChange={onChange} />);

    // Open the dropdown
    const trigger = screen.getByRole('combobox');
    fireEvent.click(trigger);

    // Click on native option
    const listbox = await screen.findByRole('listbox');
    const nativeOption = within(listbox).getByRole('option', { name: /native/i });
    fireEvent.click(nativeOption);

    expect(onChange).toHaveBeenCalledWith('native');
  });

  it('respects disabled state', () => {
    renderWithProviders(<MethodologySelector {...defaultProps} disabled />);

    const trigger = screen.getByRole('combobox');
    expect(trigger).toBeDisabled();
  });

  it('uses idPrefix for accessibility', () => {
    renderWithProviders(<MethodologySelector {...defaultProps} idPrefix="test" />);

    const trigger = screen.getByRole('combobox');
    expect(trigger).toHaveAttribute('id', 'test-methodology');
    expect(trigger).toHaveAttribute('aria-describedby', 'test-methodology-help');

    // Verify help text has correct id
    const helpText = screen.getByText(/choose which methodology plugin/i);
    expect(helpText).toHaveAttribute('id', 'test-methodology-help');
  });

  describe('accessibility', () => {
    it('links trigger to help text via aria-describedby', () => {
      renderWithProviders(<MethodologySelector {...defaultProps} />);

      const trigger = screen.getByRole('combobox');
      const helpText = screen.getByText(/choose which methodology plugin/i);

      expect(trigger).toHaveAttribute('aria-describedby', 'methodology-help');
      expect(helpText).toHaveAttribute('id', 'methodology-help');
    });

    it('has proper label association', () => {
      renderWithProviders(<MethodologySelector {...defaultProps} />);

      const trigger = screen.getByRole('combobox');
      expect(trigger).toHaveAttribute('id', 'methodology');

      // Label should be associated via htmlFor
      const label = screen.getByText('Methodology');
      expect(label).toHaveAttribute('for', 'methodology');
    });
  });
});

describe('MethodologySelector with unverified methodology', () => {
  const defaultProps = {
    value: 'bmad',
    onChange: vi.fn()
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Return unverified community methodology
    mockUseMethodologies.mockReturnValue({
      methodologies: [
        {
          name: 'native',
          version: '1.0.0',
          description: 'Built-in methodology',
          author: 'Auto Claude',
          complexity_levels: ['quick', 'standard', 'complex'],
          execution_modes: ['full_auto', 'semi_auto'],
          is_verified: true,
        },
        {
          name: 'bmad',
          version: '0.1.0',
          description: 'BMAD methodology for comprehensive planning',
          author: 'Community',
          complexity_levels: ['standard', 'complex'],
          execution_modes: ['semi_auto'],
          is_verified: false,
        }
      ],
      isLoading: false,
      error: null,
      refetch: vi.fn()
    });
  });

  it('shows Community badge for unverified methodologies in trigger', () => {
    renderWithProviders(<MethodologySelector {...defaultProps} />);

    const trigger = screen.getByRole('combobox');
    expect(trigger).toHaveTextContent(/bmad/i);
    expect(trigger).toHaveTextContent(/community/i);
  });

  it('shows Community badge for unverified methodologies in dropdown', async () => {
    renderWithProviders(<MethodologySelector {...defaultProps} />);

    // Open the dropdown
    const trigger = screen.getByRole('combobox');
    fireEvent.click(trigger);

    // Check both badges are present
    const listbox = await screen.findByRole('listbox');
    expect(within(listbox).getByText('Verified')).toBeInTheDocument();
    expect(within(listbox).getByText('Community')).toBeInTheDocument();
  });

  it('shows warning styling on Community badge', async () => {
    renderWithProviders(<MethodologySelector {...defaultProps} />);

    // Open the dropdown
    const trigger = screen.getByRole('combobox');
    fireEvent.click(trigger);

    const listbox = await screen.findByRole('listbox');
    // Find the Community text and then find the Badge element that contains it
    const communityText = within(listbox).getByText('Community');
    // The Badge wraps the text, find the parent span with badge classes
    const communityBadge = communityText.closest('[class*="border-warning"]');
    expect(communityBadge).not.toBeNull();
    expect(communityBadge).toHaveClass('text-warning');
  });
});

describe('MethodologySelector loading state', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Return loading state with no methodologies
    mockUseMethodologies.mockReturnValue({
      methodologies: [],
      isLoading: true,
      error: null,
      refetch: vi.fn()
    });
  });

  it('shows loading state when methodologies are being fetched', () => {
    renderWithProviders(<MethodologySelector value="" onChange={vi.fn()} />);

    const trigger = screen.getByRole('combobox');
    expect(trigger).toHaveTextContent(/loading methodologies/i);
  });

  it('disables the selector while loading', () => {
    renderWithProviders(<MethodologySelector value="" onChange={vi.fn()} />);

    const trigger = screen.getByRole('combobox');
    expect(trigger).toBeDisabled();
  });
});

describe('MethodologySelector error state', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Return error state
    mockUseMethodologies.mockReturnValue({
      methodologies: [],
      isLoading: false,
      error: 'Failed to load methodologies',
      refetch: vi.fn()
    });
  });

  it('shows error message when loading fails', async () => {
    renderWithProviders(<MethodologySelector value="" onChange={vi.fn()} />);

    // Open the dropdown
    const trigger = screen.getByRole('combobox');
    fireEvent.click(trigger);

    // Check error is shown in dropdown content
    await waitFor(() => {
      expect(screen.getByText('Failed to load methodologies')).toBeInTheDocument();
    });
  });
});

describe('MethodologySelector empty state', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Return empty methodologies (not loading, no error)
    mockUseMethodologies.mockReturnValue({
      methodologies: [],
      isLoading: false,
      error: null,
      refetch: vi.fn()
    });
  });

  it('shows empty message when no methodologies available', async () => {
    renderWithProviders(<MethodologySelector value="" onChange={vi.fn()} />);

    // Open the dropdown
    const trigger = screen.getByRole('combobox');
    fireEvent.click(trigger);

    // Check empty state message
    await waitFor(() => {
      expect(screen.getByText('No methodologies available')).toBeInTheDocument();
    });
  });
});
