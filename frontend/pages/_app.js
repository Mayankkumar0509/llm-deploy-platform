
import "../styles/globals.css";
import DarkModeToggle from "../components/DarkModeToggle";
import NavBar from "../components/NavBar";

export default function App({ Component, pageProps }) {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition">
      <NavBar />
      <Component {...pageProps} />
      <DarkModeToggle />
    </div>
  );
}
