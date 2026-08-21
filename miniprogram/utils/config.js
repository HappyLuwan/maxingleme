// utils/config.js
// 全局配置：后端 API 地址等
//
// ==================================================
// 【重要】部署到微信云托管后，走的是 wx.cloud.callContainer，
// 不再走 wx.request，所以 apiBaseUrl 在生产环境不再使用。
// 见 utils/api.js。
// ==================================================

const config = {
  // ===== 云托管配置（生产用）=====
  // 云托管环境 ID，在 mp 后台 → 云开发 → 环境 → 环境ID
  cloudEnv: 'prod-d6g8qda601a1eddc7',
  // 云托管服务名
  cloudService: 'maxingleme-server',

  // ===== 本地开发用（调试期直连 http://localhost:8080）=====
  // 走 wx.request 的场景（如 devtools 里勾了"不校验合法域名"）
  apiBaseUrl: 'http://localhost:8080',

  // ===== 通用 =====
  // 是否使用云托管调用（生产环境 true，本地开发 false）
  useCloudContainer: true,

  // 请求超时（毫秒）
  requestTimeout: 30000
}

module.exports = config
