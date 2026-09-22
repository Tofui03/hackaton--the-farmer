import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ExportModal } from './ExportModal';

it('UI-EXP-001 displays blocking emails with review links', () => {
  render(<MemoryRouter><ExportModal open onClose={() => undefined} blocked={{ code: 'EXPORT_BLOCKED', message: 'Cannot export', details: [], retryable: false, blocking_emails: ['email-1', 'email-2'] }} /></MemoryRouter>);
  expect(screen.getByText(/DC-08/)).toBeInTheDocument();
  expect(screen.getByText(/email-1/).closest('a')).toHaveAttribute('href', '/cases/email-1/review');
  expect(screen.getByText(/email-2/).closest('a')).toHaveAttribute('href', '/cases/email-2/review');
});
