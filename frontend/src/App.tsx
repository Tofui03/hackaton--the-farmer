import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { CaseDetailView } from './views/CaseDetailView';
import { CaseQueueView } from './views/CaseQueueView';
import { ReviewWorkspaceView } from './views/ReviewWorkspaceView';

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/cases" replace />} />
        <Route path="/cases" element={<CaseQueueView />} />
        <Route path="/cases/:emailId" element={<CaseDetailView />} />
        <Route path="/cases/:emailId/review" element={<ReviewWorkspaceView />} />
        <Route path="*" element={<Navigate to="/cases" replace />} />
      </Routes>
    </AppShell>
  );
}
