import { useRouter } from "next/router";
import { clearToken } from "../lib/auth";

export default function NavBar() {
  const router = useRouter();

  function logout() {
    clearToken();
    router.push("/");
  }

  return (
    <nav className="w-full bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 p-3 mb-4 flex justify-between items-center">
      <div className="flex space-x-4">
        <a href="/dashboard" className="text-blue-600 dark:text-blue-400">
          Dashboard
        </a>
        <a href="/deployments" className="text-blue-600 dark:text-blue-400">
          Deployments
        </a>
      </div>

      <button
        onClick={logout}
        className="text-red-600 dark:text-red-400 font-semibold"
      >
        Logout
      </button>
    </nav>
  );
}
