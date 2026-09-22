import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';
import { makeReviewRecord } from './test/recordFactory';

const getAudit = vi.fn();
vi.mock('./api/client', () => ({
  getAudit: (...args: unknown[]) => getAudit(...args),
  submitReview: vi.fn(),
  listAudits: vi.fn(),
  getSubmission: vi.fn(),
  ApiError: class ApiError extends Error { status = 500; payload = null; },
}));

import App from './App';

it('UI-REV-001 mounts the dedicated review workspace route', async () => {
  getAudit.mockResolvedValue(makeReviewRecord());
  render(<MemoryRouter initialEntries={['/cases/email-test-001/review']}><App /></MemoryRouter>);
  await waitFor(() => expect(screen.getByText('Human Review Workspace')).toBeInTheDocument());
  expect(screen.getByText('Conflicting values found')).toBeInTheDocument();
});
