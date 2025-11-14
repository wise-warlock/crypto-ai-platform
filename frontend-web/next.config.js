/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
      };
    }
    return config;
  },
};

// ĐỔI DÒNG NÀY:
module.exports = nextConfig; // <-- Sửa 'export default' thành 'module.exports ='