import api from "../lib/api";
import { saveToken } from "../lib/auth";
import AuthForm from "../components/AuthForm";
import { useRouter } from "next/router";

export default function Login() {
  const router = useRouter();

  async function login({ email, password }) {
    const res = await api.post("/auth/login", { email, password });
    saveToken(res.data.token);
    router.push("/dashboard");
  }

  return (
    <div className="mt-12">
      <h1 className="text-xl font-semibold mb-4">Login</h1>
      <AuthForm onSubmit={login} submitLabel="Login" />
      <p className="mt-4 text-sm">
        No account?{" "}
        <a className="text-sky-600 hover:underline" href="/register">
          Register
        </a>
      </p>
    </div>
  );
}
