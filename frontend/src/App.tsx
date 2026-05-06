import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { Dashboard } from "./pages/Dashboard";
import { Upload } from "./pages/Upload";
import { ReviewExtraction } from "./pages/ReviewExtraction";
import { CaseDetail } from "./pages/CaseDetail";
import { Login } from "./pages/Login";
import { RequireAuth } from "./components/RequireAuth";

function AppLayout() {
  const { pathname } = useLocation();
  const isLogin = pathname === "/login";

  return (
    <div className="min-h-screen flex">
      {!isLogin && <Sidebar />}
      <main className={`flex-1 p-6 ${isLogin ? "flex items-center justify-center" : ""}`}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <RequireAuth>
                <Dashboard />
              </RequireAuth>
            }
          />
          <Route
            path="/upload"
            element={
              <RequireAuth roles={["uploader", "admin"]}>
                <Upload />
              </RequireAuth>
            }
          />
          <Route
            path="/cases/:caseId/review"
            element={
              <RequireAuth roles={["reviewer", "admin"]}>
                <ReviewExtraction />
              </RequireAuth>
            }
          />
          <Route
            path="/cases/:caseId"
            element={
              <RequireAuth>
                <CaseDetail />
              </RequireAuth>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return <AppLayout />;
}

