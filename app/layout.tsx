import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Persona Graph — GTM Engineer",
  description: "Buyer-persona intel graph for the GTM Engineer persona",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
