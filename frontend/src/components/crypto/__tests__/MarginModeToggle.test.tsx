import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { MarginModeToggle } from '../MarginModeToggle';

describe('MarginModeToggle', () => {
  it('renders margin mode toggle with ISOLATED selected', () => {
    render(<MarginModeToggle value="ISOLATED" onChange={vi.fn()} />);
    expect(screen.getByLabelText('Isolated')).toBeChecked();
    expect(screen.getByLabelText('Cross')).not.toBeChecked();
  });

  it('renders margin mode toggle with CROSS selected', () => {
    render(<MarginModeToggle value="CROSS" onChange={vi.fn()} />);
    expect(screen.getByLabelText('Cross')).toBeChecked();
    expect(screen.getByLabelText('Isolated')).not.toBeChecked();
  });

  it('calls onChange when switching to CROSS mode', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<MarginModeToggle value="ISOLATED" onChange={onChange} />);

    await user.click(screen.getByLabelText('Cross'));
    expect(onChange).toHaveBeenCalledWith('CROSS');
  });

  it('calls onChange when switching to ISOLATED mode', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<MarginModeToggle value="CROSS" onChange={onChange} />);

    await user.click(screen.getByLabelText('Isolated'));
    expect(onChange).toHaveBeenCalledWith('ISOLATED');
  });

  it('displays help tooltip icon', () => {
    render(<MarginModeToggle value="ISOLATED" onChange={vi.fn()} />);
    expect(screen.getByText('Margin Mode')).toBeInTheDocument();
  });
});
