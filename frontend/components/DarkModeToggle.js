import { useEffect, useState } from "react";

export default function DarkModeToggle() {
  const [enabled, setEnabled] = useState(false);

  // On page load
  useEffect(() => {
    const saved = localStorage.getItem("darkmode");
    if (saved === "true") {
      document.documentElement.classList.add("dark");
      setEnabled(true);
    }
  }, []);

  function toggle() {
    const newVal = !enabled;
    setEnabled(newVal);

    if (newVal) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("darkmode", "true");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("darkmode", "false");
    }
  }

  return (
    <button
      onClick={toggle}
      className="
        fixed bottom-4 right-4 z-50 
        p-3 rounded-full shadow-lg 
        bg-gray-800 text-white 
        dark:bg-gray-300 dark:text-black
        transition
      "
    >
      {enabled ? "☀️" : "🌙"}
    </button>
  );
}
