import "../styles/globals.css";
import NavBar from "../components/NavBar";
import { useEffect } from "react";

export default function MyApp({ Component, pageProps }) {
  useEffect(() => {
    console.log("App mounted");
  }, []);

  return (
    <>
      <NavBar />
      <Component {...pageProps} />
    </>
  );
}
