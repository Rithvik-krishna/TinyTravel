import "./globals.css";
import Link from "next/link";
export const metadata = { title: "TinyTravel", description: "The price you see isn't the price you pay." };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en"><body>
      <header className="border-b border-slate-200 dark:border-slate-800 px-4 py-3 flex gap-4 text-sm items-center">
        <Link href="/search" className="font-semibold">TinyTravel</Link>
        {["onboarding","search","investigation","compare","evidence","verdict"].map(p => (
          <Link key={p} href={`/${p}`} className="text-slate-500 hover:underline">{p}</Link>
        ))}
      </header>
      <main className="max-w-5xl mx-auto p-4">{children}</main>
    </body></html>
  );
}
