import api from "../lib/api";
import { saveToken } from "../lib/auth";
import AuthForm from "../components/AuthForm";
import { useRouter } from "next/router";

export default function Register() {
  const router = useRouter();

  async function register({ email, password }) {
    const res = await api.post("/auth/register", { email, password });
    saveToken(res.data.token);
    router.push("/dashboard");
  }

  return (
    <div className="mt-12">
      <h1 className="text-xl font-semibold mb-4">Register</h1>
      <AuthForm onSubmit={register} submitLabel="Register" />
    </div>
  );
}

