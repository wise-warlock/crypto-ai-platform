// frontend-web/app/layout.tsx

import type { Metadata } from "next";
// Import file CSS toàn cục
import "./globals.css";

// Metadata này sẽ giúp SEO và hiển thị tab trên trình duyệt
export const metadata: Metadata = {
  title: "Crypto AI Platform",
  description: "Xây dựng website ứng dụng AI Agents và LLMs trong phân tích thị trường.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      {/* Nội dung từ file page.tsx sẽ được chèn vào
        bên trong thẻ <main> ở file globals.css
      */}
      <body>
        <main>{children}</main>
      </body>
    </html>
  );
}