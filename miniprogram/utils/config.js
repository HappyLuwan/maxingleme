// utils/config.js
// 全局配置：后端 API 地址等
//
// ==================================================
// 🔄 本地测试 ↔ 云托管生产 切换指南
// ==================================================
// ▶ 本地测试：useCloudContainer = false
//    需要：① 本机后端已启动（cd server-py && source .env && python -m uvicorn main:app --port 8080）
//         ② 开发者工具 → 详情 → 本地设置 → ✅ 勾"不校验合法域名..."
//         ③ 验证：curl http://localhost:8080/actuator/health 返回 UP
//
// ▶ 云托管生产：useCloudContainer = true
//    需要：① 云托管服务已发布（对应 cloudService 名称）
//         ② mp 后台已把你的微信号加入体验成员
//         ③ 不受"合法域名校验"约束（wx.cloud.callContainer 不走 http）
//
// 改完只需保存 + 点"编译"，1 秒生效。
// ==================================================

const config = {
  // ===== 云托管配置（生产用）=====
  // 云托管环境 ID：mp 后台 → 云开发 → 环境 → 环境ID
  cloudEnv: 'prod-d6g8qda601a1eddc7',
  // 云托管服务名（必须与云托管控制台里的服务名完全一致）
  cloudService: 'flask-ejik',

  // ===== 本地开发用（直连本机后端）=====
  apiBaseUrl: 'http://localhost:8080',

  // ===== 🔥 唯一开关：切换本地/云托管 =====
  // false = 走 wx.request 请求 apiBaseUrl（本地）
  // true  = 走 wx.cloud.callContainer 请求云托管服务
  useCloudContainer: true,

  // 请求超时（毫秒）
  requestTimeout: 30000
}

module.exports = config
