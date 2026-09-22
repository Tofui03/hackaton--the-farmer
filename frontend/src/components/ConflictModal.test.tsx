import { fireEvent, render, screen } from '@testing-library/react';
import { ConflictModal } from './ConflictModal';

it('UI-REV-003 exposes explicit conflict recovery actions', () => {
  const reload = vi.fn();
  const diff = vi.fn();
  render(<ConflictModal open message="current revision is 3" onReload={reload} onReviewDifferences={diff} onClose={() => undefined} />);
  expect(screen.getByText('Revision Conflict Detected')).toBeInTheDocument();
  fireEvent.click(screen.getByText('Review Differences'));
  fireEvent.click(screen.getByText('Reload Latest Server Version'));
  expect(diff).toHaveBeenCalledTimes(1);
  expect(reload).toHaveBeenCalledTimes(1);
});
