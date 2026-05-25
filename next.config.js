/** @type {import('next').NextConfig} */
const nextConfig = {
  // better-sqlite3 is a native module — mark it external so Next.js
  // doesn't try to bundle it into the server build.
  serverExternalPackages: ["better-sqlite3"],
};

module.exports = nextConfig;
