import { useEffect, useState } from "react";
import api from "../lib/api";
import { getToken } from "../lib/auth";
import { useRouter } from "next/router";

export default function Deployments() {
  const router = useRouter();
  const [deployments, setDeployments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) return router.push("/");

    load();
  }, [router]);

  async function load() {
    try {
      const r = await api.get("/deployments");
      setDeployments(r.data.deployments || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }

  return (
    <div className="p-4 max-w-xl mx-auto dark:text-white">
      <h1 className="text-xl font-bold mb-4 text-center">Past Deployments</h1>

      {loading && (
        <p className="text-center text-gray-500 dark:text-gray-300">
          Loading...
        </p>
      )}

      {deployments.length === 0 && !loading && (
        <p className="text-center text-gray-400 dark:text-gray-500">
          No deployments yet.
        </p>
      )}

      <div className="space-y-4">
        {deployments.map((d) => (
          <div
            key={d.id}
            className="border rounded-lg p-4 bg-white dark:bg-gray-800 dark:border-gray-700"
          >
            <div className="flex justify-between items-center">
              <div>
                <div className="font-semibold text-blue-600 dark:text-blue-400 text-sm break-all">
                  {d.task}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  Round {d.round} • {new Date(d.created_at).toLocaleString()}
                </div>
              </div>

              <div
                className={`text-xs px-2 py-1 rounded ${
                  d.status.startsWith("error")
                    ? "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300"
                    : d.status === "success"
                    ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                    : "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200"
                }`}
              >
                {d.status}
              </div>
            </div>

            {d.repo_url && (
              <a
                href={d.repo_url}
                target="_blank"
                rel="noopener noreferrer"
                className="block mt-3 text-blue-600 dark:text-blue-400 text-sm truncate"
              >
                🔧 GitHub Repo
              </a>
            )}

            {d.pages_url && (
              <a
                href={d.pages_url}
                target="_blank"
                rel="noopener noreferrer"
                className="block mt-1 text-blue-600 dark:text-blue-400 text-sm truncate"
              >
                🌐 View Live Website
              </a>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
