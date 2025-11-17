import { useState } from "react";

export default function AuthForm({ onSubmit, submitLabel = "Submit" }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  async function handle(e) {
    e.preventDefault();
    setErr(null);
    setLoading(true);

    try {
      await onSubmit({ email, password });
    } catch (error) {
      setErr(error?.response?.data?.detail || error.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handle} className="max-w-md space-y-4">
      {err && <div className="p-2 border border-red-300 bg-red-50">{err}</div>}

      <div>
        <label>Email</label>
        <input
          className="block w-full border p-2 rounded mt-1"
          required
          type="email"
          value={email}
          onChange={(e)=>setEmail(e.target.value)}
        />
      </div>

      <div>
        <label>Password</label>
        <input
          className="block w-full border p-2 rounded mt-1"
          required
          type="password"
          value={password}
          onChange={(e)=>setPassword(e.target.value)}
        />
      </div>

      <button className="w-full py-2 bg-sky-600 text-white rounded">
        {loading ? "Loading..." : submitLabel}
      </button>
    </form>
  );
}

