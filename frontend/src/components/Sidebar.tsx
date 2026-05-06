import { NavLink } from "react-router-dom";
import { setSession } from "../api/client";
import { useSession } from "../api/sessionStore";

function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        [
          "block px-3 py-2 rounded-md text-sm font-medium",
          isActive ? "bg-slate-800 text-white" : "text-slate-300 hover:bg-slate-900 hover:text-white"
        ].join(" ")
      }
    >
      {label}
    </NavLink>
  );
}

export function Sidebar() {
  const session = useSession();

  return (
    <aside className="w-72 border-r border-slate-800 bg-[#0B1222] h-screen sticky top-0 p-4 flex flex-col overflow-y-auto">
      <div className="mb-6">
        <div className="text-lg font-semibold tracking-tight">AadeshPaalan</div>
        <div className="text-xs text-slate-400">Court compliance execution overlay</div>
      </div>

      <nav className="space-y-1 flex-1">
        <NavItem to="/" label="Dashboard" />
        <NavItem to="/upload" label="Upload Judgment" />
      </nav>

      <div className="pt-4 border-t border-slate-800">
        {session ? (
          <div className="space-y-2">
            <div className="text-xs text-slate-400">Signed in</div>
            <div className="text-sm font-medium">{session.name}</div>
            <div className="text-xs text-slate-400">Role: {session.role}</div>
            <button
              className="w-full mt-2 px-3 py-2 rounded-md bg-slate-800 hover:bg-slate-700 text-sm"
              onClick={() => setSession(null)}
            >
              Sign out
            </button>
          </div>
        ) : (
          <div className="text-xs text-slate-400">Not signed in</div>
        )}
      </div>
    </aside>
  );
}

