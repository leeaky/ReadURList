import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ReadURList",
  description: "Personal reading corpus",
  icons: {
    icon: "/logo.png",
    apple: "/apple-icon.png",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
