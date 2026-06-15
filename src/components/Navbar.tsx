import { Link, useLocation } from "react-router-dom";

interface NavbarProps {
  onLoginClick: () => void;
}

export default function Navbar({ onLoginClick }: NavbarProps) {
  const location = useLocation();
  const isLoggedIn = !!localStorage.getItem("token");

  const handleLogout = () => {
    // JWT logout is purely client-side: drop the stored credentials...
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    // ...and reload onto /events, which will show the logged-out prompt.
    window.location.href = "/events";
  };

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/events" style={{ textDecoration: "none", color: "inherit" }}>
          PenguWave 🐧
        </Link>
      </div>
      <div className="navbar-links">
        <Link
          to="/events"
          className={location.pathname.startsWith("/events") ? "active" : ""}
        >
          Events
        </Link>
        <Link
          to="/users"
          className={location.pathname === "/users" ? "active" : ""}
        >
          Users
        </Link>
        {isLoggedIn ? (
          <button onClick={handleLogout} className="navbar-login-btn">
            Logout
          </button>
        ) : (
          <button onClick={onLoginClick} className="navbar-login-btn">
            Login
          </button>
        )}
      </div>
    </nav>
  );
}
