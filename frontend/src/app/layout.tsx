import type { Metadata } from "next";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Plan Contingencia",
  description: "Planes de continuidad de negocio con cobro x402 en Monad",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body style={{ fontFamily: "system-ui", maxWidth: 960, margin: "0 auto", padding: 24 }}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
