import type { Metadata } from "next";
import { ConvexClientProvider } from "@/providers/ConvexClientProvider";
import { I18nProvider } from "@/providers/I18nProvider";
import { CLOUD_MODE } from "@/lib/cloud-mode";
import "./globals.css";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Auto Claude",
  description: "AI-powered software development platform",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  let token: string | null = null;

  if (CLOUD_MODE) {
    try {
      const { getToken } = await import("@/lib/auth-server");
      token = (await getToken()) ?? null;
    } catch {
      // auth-server not available in self-hosted mode
    }
  }

  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans antialiased">
        <I18nProvider>
          <ConvexClientProvider initialToken={token}>
            {children}
          </ConvexClientProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
