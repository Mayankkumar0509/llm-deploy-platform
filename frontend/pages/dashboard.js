// frontend/pages/dashboard.js
import { useEffect, useState } from "react";
import api from "../lib/api";
import { getToken } from "../lib/auth";
import { useRouter } from "next/router";

function fileToDataURI(file) {
  return new Promise((res, rej) => {
    if (!file) return res(null);
    const reader = new FileReader();
    reader.onload = () => res(reader.result);
    reader.onerror = () => rej("Unable to read file");
    reader.readAsDataURL(file);
  });
}

// System Templates
const SYSTEM_TEMPLATES = {
  "sum-of-sales": {
    title: "Sum of Sales",
    brief:
      "Publish a page that loads data.csv from attachments, sums the sales column, and shows it inside #total-sales.",
    sampleAttachmentName: "data.csv",
    sampleAttachmentContent:
      "date,product,sales\n2025-01-01,Widget,10\n2025-01-02,Gadget,20",
  },
  "markdown-to-html": {
    title: "Markdown → HTML Converter",
    brief:
      "Convert input.md to HTML using marked, render in #markdown-output, load highlight.js for code blocks.",
    sampleAttachmentName: "input.md",
    sampleAttachmentContent:
      "# Hello\nThis is Markdown.\n```js\nconsole.log('test')\n```",
  },
  "captcha-solver": {
    title: "Captcha Solver",
    brief:
      "Create a captcha solver that reads an image from ?url= and displays the solved text on page.",
    sampleAttachmentName: "sample.png",
    sampleAttachmentContent: "",
  },
  "github-user": {
    title: "GitHub User Info",
    brief:
      "Fetch GitHub user data and display account creation date inside #github-created-at.",
    sampleAttachmentName: "",
    sampleAttachmentContent: "",
  },
};

export default function Dashboard() {
  const router = useRouter();

  const [me, setMe] = useState(null);

  // Form Data
  const [taskKey, setTaskKey] = useState("");
  const [customTaskName, setCustomTaskName] = useState("");
  const [customBrief, setCustomBrief] = useState("");
  const [round, setRound] = useState(1);
  const [attachmentFile, setAttachmentFile] = useState(null);
  const [evalUrl, setEvalUrl] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [githubToken, setGithubToken] = useState("");

  const [loading, setLoading] = useState(false);
  const [deployments, setDeployments] = useState([]);
  const [modal, setModal] = useState(null);

  useEffect(() => {
  const token = getToken();
  if (!token) return router.push("/");

  api.get("/me")
    .then((r) => {
      setMe(r.data);
      return api.get("/deployments");
    })
    .then((r) => {
      setDeployments(r.data.deployments || []);
    })
    .catch(() => router.push("/"));
}, []);

  async function loadDeployments() {
    try {
      const r = await api.get("/deployments");
      setDeployments(r.data.deployments || []);
    } catch (e) {}
  }

  function getActiveTemplate() {
    if (taskKey === "") return null;
    if (taskKey === "custom") return null;
    return SYSTEM_TEMPLATES[taskKey];
  }

  function placeholderBrief() {
    const t = getActiveTemplate();
    if (!t) return "Write a custom brief here...";
    return t.brief;
  }

  async function handleDeploy() {
    setLoading(true);
    try {
      const attachments = [];

      if (attachmentFile) {
        const datauri = await fileToDataURI(attachmentFile);
        attachments.push({
          name: attachmentFile.name,
          url: datauri,
        });
      } else {
        // fallback to sample attachment if template has one
        const template = getActiveTemplate();
        if (template && template.sampleAttachmentName && template.sampleAttachmentContent) {
          const base64 = btoa(unescape(encodeURIComponent(template.sampleAttachmentContent)));
          attachments.push({
            name: template.sampleAttachmentName,
            url: `data:text/plain;base64,${base64}`,
          });
        }
      }

      // Build task name
      const finalTaskName =
        taskKey === "custom"
          ? customTaskName.trim() || `custom-task-${Date.now()}`
          : taskKey;

      // Build brief
      const template = getActiveTemplate();
      const finalBrief =
        customBrief.trim() !== ""
          ? customBrief.trim()
          : template
          ? template.brief
          : "Custom task brief";

      const nonce = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
      const taskID = `${finalTaskName}-${nonce.slice(0, 6)}`;

      const payload = {
        email: me.email,
        secret: process.env.NEXT_PUBLIC_STUDENT_SECRET || "",
        task: taskID,
        round: Number(round),
        nonce,
        brief: finalBrief,
        checks: [],
        evaluation_url: evalUrl || undefined,
        attachments,
        target_repo: repoUrl || undefined,
        target_github_token: githubToken || undefined,
      };

      const res = await api.post("/api-endpoint", payload);

      setModal({
        title: "Deployment Started",
        body: res.data,
      });

      setTimeout(loadDeployments, 1500);
    } catch (err) {
      console.error(err);
      alert("Deployment failed: " + (err?.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-4 max-w-xl mx-auto">
      <h1 className="text-xl font-bold mb-4 text-center">Task Deployment</h1>

      {/** USER INFO */}
      <div className="bg-white shadow p-3 rounded mb-4 text-center">
        Logged in as <b>{me?.email}</b>
      </div>

      {/** TEMPLATE SELECTOR */}
      <label className="font-semibold">Select Task Template</label>
      <select
        className="w-full border rounded p-2 mt-1 mb-4"
        value={taskKey}
        onChange={(e) => setTaskKey(e.target.value)}
      >
        <option value="">-- choose --</option>

        {Object.entries(SYSTEM_TEMPLATES).map(([k, v]) => (
          <option key={k} value={k}>
            {v.title}
          </option>
        ))}

        <option value="custom">➕ Custom Task Template</option>
      </select>

      {/** CUSTOM TEMPLATE NAME */}
      {taskKey === "custom" && (
        <div className="mb-4">
          <label className="font-semibold">Custom Task Template Name</label>
          <input
            className="w-full border rounded p-2 mt-1"
            placeholder="my-unique-task-123"
            value={customTaskName}
            onChange={(e) => setCustomTaskName(e.target.value)}
          />
        </div>
      )}

      {/** ROUND */}
      <label className="font-semibold">Round</label>
      <select
        className="w-full border rounded p-2 mt-1 mb-4"
        value={round}
        onChange={(e) => setRound(e.target.value)}
      >
        <option value={1}>1</option>
        <option value={2}>2</option>
      </select>

      {/** BRIEF */}
      <label className="font-semibold">Brief (optional)</label>
      <textarea
        className="w-full border rounded p-2 mt-1 mb-4"
        placeholder={placeholderBrief()}
        value={customBrief}
        onChange={(e) => setCustomBrief(e.target.value)}
      />

      {/** ATTACHMENT */}
      <label className="font-semibold">Attachment File (optional)</label>
      <input
        type="file"
        className="w-full mt-1 mb-4"
        onChange={(e) => setAttachmentFile(e.target.files[0])}
      />

      {/** OPTIONAL EVAL URL */}
      <label className="font-semibold">Evaluation URL (optional)</label>
      <input
        className="w-full border rounded p-2 mt-1 mb-4"
        placeholder="https://example.com/notify"
        value={evalUrl}
        onChange={(e) => setEvalUrl(e.target.value)}
      />

      {/** OPTIONAL REPO URL */}
      <label className="font-semibold">GitHub Repo URL (optional)</label>
      <input
        className="w-full border rounded p-2 mt-1 mb-4"
        placeholder="https://github.com/user/repo"
        value={repoUrl}
        onChange={(e) => setRepoUrl(e.target.value)}
      />
      <p className="text-xs text-gray-500 mb-4">
        Provide only if you want files pushed to your own repo.
      </p>

      {/** OPTIONAL TOKEN */}
      <label className="font-semibold">GitHub Token (optional)</label>
      <input
        className="w-full border rounded p-2 mt-1 mb-4"
        placeholder="ghp_xxxxxxxxxxxx"
        value={githubToken}
        onChange={(e) => setGithubToken(e.target.value)}
      />

      {/** DEPLOY BUTTON */}
      <button
        onClick={handleDeploy}
        disabled={loading}
        className="w-full bg-blue-600 text-white py-2 rounded mt-2"
      >
        {loading ? "Deploying..." : "Deploy"}
      </button>

      {/** DEPLOYMENT HISTORY */}
      <h2 className="text-lg font-semibold mt-6 mb-2">Recent Deployments</h2>
      <div className="space-y-3">
        {deployments.map((d) => (
          <div key={d.id} className="border p-3 rounded bg-white">
            <div className="font-semibold">{d.task}</div>
            <div className="text-sm text-gray-500">round {d.round}</div>
            <div className="text-sm text-gray-600 mt-1">{d.status}</div>

            {d.repo_url && (
              <a
                href={d.repo_url}
                target="_blank"
                className="text-blue-600 text-sm"
              >
                Repo ↗
              </a>
            )}

            {d.pages_url && (
              <a
                href={d.pages_url}
                target="_blank"
                className="text-blue-600 text-sm ml-3"
              >
                Website ↗
              </a>
            )}
          </div>
        ))}
      </div>

      {/** SUCCESS MODAL */}
      {modal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center px-4">
          <div className="bg-white p-6 rounded shadow-lg w-full max-w-md">
            <h3 className="text-lg font-semibold mb-2">{modal.title}</h3>
            <pre className="bg-gray-100 p-3 rounded max-h-60 overflow-auto text-xs">
              {JSON.stringify(modal.body, null, 2)}
            </pre>
            <button
              className="w-full border mt-4 py-2 rounded"
              onClick={() => setModal(null)}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

