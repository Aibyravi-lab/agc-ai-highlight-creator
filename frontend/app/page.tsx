"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [message, setMessage] = useState("Connecting to AGC Backend...");

  useEffect(() => {
    fetch("http://localhost:8000")
      .then((response) => response.json())
      .then((data) => {
        setMessage(data.message);
      })
      .catch(() => {
        setMessage("Backend connection failed ❌");
      });
  }, []);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center">
      <h1 className="text-5xl font-bold">
        🎮 AGC
      </h1>

      <p className="mt-4 text-2xl">
        AI Gaming Highlight Creator
      </p>

      <div className="mt-8 text-xl">
        {message}
      </div>
    </main>
  );
}