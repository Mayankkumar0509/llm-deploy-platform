import "../styles/globals.css";
import { useEffect } from "react";
import NavBar from "../components/NavBar";

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
