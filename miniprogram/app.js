// app.js
const config = require('./utils/config')

App({
  onLaunch() {
    // 初始化云能力（云托管调用依赖）
    if (!wx.cloud) {
      console.error('当前微信版本过低，无法使用云能力，请升级到 2.2.3 以上')
    } else {
      wx.cloud.init({
        env: config.cloudEnv,
        traceUser: true
      })
    }

    // 本地日志
    const logs = wx.getStorageSync('logs') || []
    logs.unshift(Date.now())
    wx.setStorageSync('logs', logs)
  },
  globalData: {
    userInfo: null
  }
})
