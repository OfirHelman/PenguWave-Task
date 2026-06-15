import { useState } from "react";

interface LoginModalProps {
  onClose: () => void;
}

export default function LoginModal({ onClose }: LoginModalProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    try {
      const res = await fetch("http://localhost:3001/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (res.ok) {
        // Success: persist the token + role, then close the modal.
        const data = await res.json();
        localStorage.setItem("token", data.token);
        localStorage.setItem("role", data.user.role);
        onClose();
      } else {
        // 401 (or any non-OK): show an error and keep the modal open.
        setError("Invalid email or password");
      }
    } catch {
      // Network/backend unreachable — surface it without closing.
      setError("Unable to reach the server. Please try again.");
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>
          ✕
        </button>
        <h2>Sign In</h2>
        <p style={{ color: "#666", marginBottom: 20, fontSize: 14 }}>
          Enter your credentials to access PenguWave
        </p>
        {error && (
          <p style={{ color: "#c0392b", marginBottom: 16, fontSize: 14 }}>
            {error}
          </p>
        )}
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 12 }}>
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
            />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>
          <button type="submit" className="btn-primary" style={{ width: "100%" }}>
            Sign In
          </button>
        </form>
      </div>
    </div>
  );
}
