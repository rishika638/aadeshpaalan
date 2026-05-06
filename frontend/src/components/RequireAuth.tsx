import { Navigate, useLocation } from "react-router-dom";
import type { UserRole } from "../types/api";
import { useSession } from "../api/sessionStore";

export function RequireAuth({
  children,
  roles
}: {
  children: React.ReactNode;
  roles?: UserRole[];
}) {
  const loc = useLocation();
  const session = useSession();

  if (!session) {
    return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  }
  if (roles && !roles.includes(session.role)) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

