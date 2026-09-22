import { render, screen } from '@testing-library/react';
import { ReviewControls, type ReviewDraft } from './ReviewControls';
import { makeReviewRecord } from '../test/recordFactory';

const draft: ReviewDraft = {
  actorId: 'operator-1', rationale: 'Checked source', category: '', siDocument: '', blDocument: '', fieldDocument: '', field: 'shipper', rawValue: '', evidenceId: '', correctionRationale: '',
};

it('UI-REV-002 humanizes logical reasons and exposes no mismatch override', () => {
  render(<ReviewControls record={makeReviewRecord()} draft={draft} onChange={() => undefined} onSubmit={() => undefined} submitting={false} />);
  expect(screen.getByText('Conflicting values found')).toBeInTheDocument();
  expect(screen.queryByLabelText(/mismatch/i)).not.toBeInTheDocument();
  expect(screen.getByText(/Match booleans cannot be edited/)).toBeInTheDocument();
});
