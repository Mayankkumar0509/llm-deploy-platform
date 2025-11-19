/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  experimental: {
    optimizePackageImports: [],
  },

  pageExtensions: ["js", "jsx"],

  output: "standalone",

  trailingSlash: true,
};

module.exports = nextConfig;

