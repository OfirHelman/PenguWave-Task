import { useEffect, useState } from "react";
import { User } from "../types";

const API = "http://localhost:3001/api/users";

// Build the auth header from the token saved at login.
function authHeaders() {
  const token = localStorage.getItem("token");
  return { Authorization: `Bearer ${token}` };
}

// Turn a non-OK response into a friendly message.
function messageForStatus(status: number) {
  if (status === 401) return "You are not logged in. Please sign in.";
  if (status === 403) return "You don't have permission (admin only).";
  return "Request failed. Please try again.";
}

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState("analyst");

  // Fetch the current user list from the backend.
  const loadUsers = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(API, { headers: authHeaders() });
      if (!res.ok) {
        setError(messageForStatus(res.status));
        return;
      }
      setUsers(await res.json());
    } catch {
      setError("Unable to reach the server.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEmail || !newPassword) return;
    setError("");

    try {
      const res = await fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({
          email: newEmail,
          password: newPassword,
          role: newRole,
        }),
      });

      if (!res.ok) {
        // Backend returns { error: "..." } for 400; fall back by status otherwise.
        const data = await res.json().catch(() => null);
        setError(data?.error || messageForStatus(res.status));
        return;
      }

      // Success: reset the form and refresh the list.
      setNewEmail("");
      setNewPassword("");
      setNewRole("analyst");
      setShowForm(false);
      await loadUsers();
    } catch {
      setError("Unable to reach the server.");
    }
  };

  const handleDelete = async (id: string) => {
    setError("");
    try {
      const res = await fetch(`${API}/${id}`, {
        method: "DELETE",
        headers: authHeaders(),
      });
      if (!res.ok) {
        // Prefer the backend's { error: "..." } message; fall back by status.
        const data = await res.json().catch(() => null);
        setError(data?.error || messageForStatus(res.status));
        return;
      }
      await loadUsers();
    } catch {
      setError("Unable to reach the server.");
    }
  };

  return (
    <div className="page-container">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h1>User Management</h1>
        <button className="btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "Add User"}
        </button>
      </div>

      {error && <p style={{ color: "#c0392b" }}>{error}</p>}
      {loading && <p style={{ color: "#666" }}>Loading users…</p>}

      {showForm && (
        <div style={{ border: "1px solid #ddd", padding: 16, marginBottom: 20, background: "#fafafa" }}>
          <h3 style={{ marginBottom: 12 }}>New User</h3>
          <form onSubmit={handleAddUser}>
            <div style={{ marginBottom: 8 }}>
              <label>Email</label>
              <input
                type="email"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                placeholder="user@penguwave.io"
                required
              />
            </div>
            <div style={{ marginBottom: 8 }}>
              <label>Password</label>
              <input
                type="text"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="password"
                required
              />
            </div>
            <div style={{ marginBottom: 12 }}>
              <label>Role</label>
              <select value={newRole} onChange={(e) => setNewRole(e.target.value)}>
                <option value="admin">Admin</option>
                <option value="analyst">Analyst</option>
                <option value="viewer">Viewer</option>
              </select>
            </div>
            <button type="submit" className="btn-primary">
              Create User
            </button>
          </form>
        </div>
      )}

      <table>
        <thead>
          <tr>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id}>
              <td>{user.email}</td>
              <td>{user.role}</td>
              <td>
                <span style={{ color: user.status === "active" ? "green" : "#999" }}>
                  {user.status}
                </span>
              </td>
              <td>
                <a
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    handleDelete(user.id);
                  }}
                  style={{ color: "red" }}
                >
                  Delete
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {users.length === 0 && <p style={{ color: "#999" }}>No users.</p>}
    </div>
  );
}
