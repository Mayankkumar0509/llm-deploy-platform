import Link from "next/link";
import { useRouter } from "next/router";
import { getToken, removeToken } from "../lib/auth";

export default function Header() {
  const router = useRouter();
  const token = typeof window !== "undefined" ? getToken() : null;

  function logout() {
    removeToken();
    router.push("/");
  }

  return (
    <header className="bg-white shadow-sm">
      <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
        <Link href="/dashboard" className="font-semibold text-lg">
          LLM Deploy
        </Link>

        <nav className="space-x-4">
          {token ? (
            <>
              <Link href="/dashboard">Dashboard</Link>
              <Link href="/deployments">Deployments</Link>
              <button
                onClick={logout}
                className="px-3 py-1 rounded bg-red-500 text-white ml-3"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link href="/">Login</Link>
              <Link href="/register">Register</Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
